import asyncio
import logging
import time
from typing import Annotated, Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import Depends
from qdrant_client import models
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, get_db
from app.core.exceptions import ConfigurationError, TechnicalError
from app.models.topic_stat import TopicStat
from app.repositories.topic_repository import TopicRepository
from app.repositories.vector_repository import VectorRepository
from app.services.settings_service import SettingsService, get_settings_service
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)

# Constants
BASE_TRENDING_COLLECTION = "trending_topics"
SIMILARITY_THRESHOLD = 0.90
MAX_VARIATIONS = 10
REFINEMENT_MILESTONES = {2, 3, 4, 5, 10, 20, 50, 100}

REFINEMENT_PROMPT_TEMPLATE = """# Rôle
Vous êtes un expert en rédaction et en architecture de l'information.

# Tâche
Synthétisez ces questions utilisateurs en un titre de catégorie clair, court et précis (FRANÇAIS).

# Questions
{variations_str}

# Format
- Titre court (max 6 mots)
- Question directe ou groupe nominal.
- PAS DE FORMATAGE. PAS DE "TITRE :". JUSTE LE TEXTE.
"""


class TrendingService:
    """
    Service for managing semantic trending questions with AI title refinement.

    ARCHITECT NOTE:
    - Decoupled Vector Storage via VectorRepository.
    - Improved Background Task Safety.
    - Strict Async/Await patterns.
    """

    def __init__(
        self,
        db: AsyncSession,
        repository: Optional[TopicRepository] = None,
        vector_service: Optional[VectorService] = None,
        settings_service: Optional[SettingsService] = None,
        vector_repository: Optional[VectorRepository] = None,  # P1: DI Injection
    ):
        self.db = db
        self.repository = repository or TopicRepository(db)
        self.settings_service = settings_service or SettingsService(db)
        self.vector_service = vector_service or VectorService(self.settings_service)

        # P1: Initialize Repo (Prefer injected, fallback to creating from service)
        if vector_repository:
            self.vector_repo = vector_repository
        else:
            # We use the Async client for the repo
            self.vector_repo = VectorRepository(self.vector_service.aclient)

    def _get_collection_name(self, provider: str) -> str:
        """Helper to generate provider-specific collection name."""
        provider = provider.lower().strip()
        if provider == "ollama":
            return f"{BASE_TRENDING_COLLECTION}_ollama"
        if provider in ["local", "huggingface"]:
            return f"{BASE_TRENDING_COLLECTION}_local"
        if provider == "openai":
            return f"{BASE_TRENDING_COLLECTION}_openai"
        return f"{BASE_TRENDING_COLLECTION}_gemini"

    async def process_user_question(
        self,
        question: str,
        assistant_id: UUID,
        embedding: List[float],
        embedding_provider: str = "gemini",  # Provider for vector collection, NOT for LLM
    ) -> None:
        """
        Ingestion logic for tracking trending questions.
        Matches semantically similar questions using Vector Search.
        """
        start_time = time.time()
        func_name = "TrendingService.process_user_question"
        logger.info(f"START | {func_name} | Assistant: {assistant_id} | Embedding Provider: {embedding_provider}")
        logger.debug(f"Embedding received: {len(embedding)} dimensions")

        try:
            # 1. Resolve collection based on embedding provider
            collection_name = self._get_collection_name(embedding_provider)

            # 2. Ensure collection exists (Using Service Helper)
            await self.vector_service.ensure_collection_exists(collection_name, provider=embedding_provider)

            # 3. Semantic Search via Repository (Abstracted)
            results = await (await self.vector_service.get_async_qdrant_client()).query_points(
                collection_name=collection_name,
                query=embedding,
                limit=1,
                score_threshold=SIMILARITY_THRESHOLD,
                query_filter=models.Filter(
                    must=[models.FieldCondition(key="assistant_id", match=models.MatchValue(value=str(assistant_id)))]
                ),
            )

            search_results = results.points
            logger.debug(f"Semantic search returned {len(search_results)} results")

            if search_results:
                # 3. Match Found - Update existing topic
                match = search_results[0]
                topic_id = UUID(match.id)
                logger.debug(f"Match Found | Topic ID {topic_id} | Score: {match.score:.3f}")

                await self._update_existing_topic(topic_id, question, embedding_provider=embedding_provider)
                logger.info(f"✓ Updated existing topic {topic_id}")
            else:
                # 4. No Match - Create new topic
                await self._create_new_topic(question, assistant_id, embedding, embedding_provider=embedding_provider)
                logger.info(f"✓ Created new trending topic")

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"FINISH | {func_name} | Duration: {elapsed}ms")

        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | Error: {str(e)}", exc_info=True)
            # We raise because this is likely called in ingestion flow, we want caller to know?
            # Or better, we swallow to not break the chat flow.
            # Let's swallow but log heavily. Trending failure shouldn't kill Chat.
            logger.warning("Trending processing failed, but continuing chat flow.")

    async def _update_existing_topic(self, topic_id: UUID, question: str, embedding_provider: str = "gemini"):
        """Helper to safely update existing topic."""
        topic = await self.repository.get_by_id_with_lock(topic_id)
        if not topic:
            return

        topic.frequency += 1
        variations = list(topic.raw_variations) if topic.raw_variations else []
        variations.append(question)
        if len(variations) > MAX_VARIATIONS:
            variations = variations[-MAX_VARIATIONS:]
        topic.raw_variations = variations

        await self.db.commit()
        await self.db.refresh(topic)

        # Periodic title refinement
        if topic.frequency in REFINEMENT_MILESTONES:
            # Fire and forget safely
            import asyncio

            asyncio.create_task(self._safe_refine_title_task(topic_id, embedding_provider=embedding_provider))

    async def _create_new_topic(
        self, question: str, assistant_id: UUID, embedding: List[float], embedding_provider: str = "gemini"
    ):
        """Helper to create new topic."""
        logger.info(f"No Match | Creating new topic (Embedding Provider: {embedding_provider})")

        collection_name = self._get_collection_name(embedding_provider)

        new_topic = await self.repository.create(
            {"canonical_text": question, "frequency": 1, "raw_variations": [question], "assistant_id": assistant_id}
        )

        # Upsert to Qdrant via Repository
        point = models.PointStruct(
            id=str(new_topic.id),
            vector=embedding,
            payload={
                "assistant_id": str(assistant_id),
                "canonical_text": question,
                "created_at": new_topic.created_at.isoformat() if new_topic.created_at else None,
            },
        )

        await self.vector_repo.upsert_points(collection_name, [point])

    async def _safe_refine_title_task(self, topic_id: UUID, embedding_provider: str = "gemini") -> None:
        """
        Wrapper to handle session lifecycle for background tasks.
        Note: embedding_provider is for collection selection only.
        Chat model provider is determined from the assistant.
        """
        try:
            async with SessionLocal() as db:
                # Re-inject dependencies
                settings_svc = SettingsService(db)
                vector_svc = VectorService(settings_svc)
                vector_repo = VectorRepository(await vector_svc.get_async_qdrant_client())

                service = TrendingService(
                    db=db, settings_service=settings_svc, vector_service=vector_svc, vector_repository=vector_repo
                )
                await service._refine_title(topic_id, embedding_provider=embedding_provider)
        except Exception as e:
            logger.error(f"Background Task Failed for {topic_id}: {e}", exc_info=True)

    async def _refine_title(self, topic_id: UUID, embedding_provider: str = "gemini") -> None:
        """
        Core logic for refining a trending topic title using AI.

        Args:
            topic_id: The topic to refine
            embedding_provider: Provider used for vector collection (for payload update)
                               This is NOT used for the LLM - chat provider comes from assistant
        """
        # Collection name based on embedding provider (for updating vector payload)
        collection_name = self._get_collection_name(embedding_provider)
        topic = await self.repository.get_by_id(topic_id)
        if not topic or not topic.raw_variations:
            return

        variations_str = "\n".join([f"- {v}" for v in topic.raw_variations])
        prompt = REFINEMENT_PROMPT_TEMPLATE.format(variations_str=variations_str)

        try:
            from app.models.assistant import Assistant
            from app.factories.llm_factory import LLMFactory

            # 1. Get Assistant to determine CHAT model provider (not embedding provider!)
            assistant = await self.db.get(Assistant, topic.assistant_id)
            if not assistant:
                logger.warning(f"Assistant {topic.assistant_id} not found, skipping refinement")
                return

            # 2. Use assistant's chat model provider
            chat_provider = assistant.model_provider
            logger.info(
                f"Refining topic {topic_id} | Chat Provider: {chat_provider} | Embedding Provider: {embedding_provider}"
            )

            # 3. Resolve Model Name from Settings based on Chat Provider
            # CRITICAL: Never hardcode models - always use settings from DB
            chat_model = await self.settings_service.get_value(f"{chat_provider}_chat_model")

            # 4. Validate model is configured - no fallbacks
            if not chat_model:
                raise ConfigurationError(
                    f"Model not configured for provider {chat_provider}. "
                    f"Please configure '{chat_provider}_chat_model' in settings."
                )

            # 5. Get API Key / Base URL based on Chat Provider
            api_key = None
            if chat_provider == "gemini":
                api_key = await self.settings_service.get_value("gemini_api_key")
            elif chat_provider == "openai":
                api_key = await self.settings_service.get_value("openai_api_key")
            elif chat_provider == "mistral":
                api_key = await self.settings_service.get_value("mistral_api_key")
            elif chat_provider == "ollama":
                api_key = await self.settings_service.get_value("ollama_base_url")
            elif chat_provider == "local":
                # Local might use ollama key or not needed
                pass

            llm = LLMFactory.create_llm(provider=chat_provider, model_name=chat_model, api_key=api_key, temperature=0.1)

            # P0 Fix: Add timeout to prevent hanging background tasks
            import asyncio

            response = await asyncio.wait_for(llm.acomplete(prompt), timeout=45.0)

            refined_title = self._clean_ai_title(response.text)

            # Sync DB & Vector
            await self.repository.update(topic.id, {"canonical_text": refined_title})

            # Use Repository ACL/Updater approach if possible, or direct Payload update
            # Adding payload update helper to Repo would be best, but for now we use client via repo access?
            # Or just use qdrant client from vector_service as we have it.
            await (await self.vector_service.get_async_qdrant_client()).set_payload(
                collection_name=collection_name, payload={"canonical_text": refined_title}, points=[str(topic_id)]
            )

            logger.info(f"Topic {topic_id} refined: '{refined_title}'")

        except Exception as e:
            logger.error(f"Refinement failed for {topic_id}: {e}")

    def _clean_ai_title(self, raw_text: str) -> str:
        """Clean AI output."""
        text = raw_text.strip().strip('"').strip("'")
        prefixes = ["Titre :", "Voici :", "Suggestion :"]
        for p in prefixes:
            if text.lower().startswith(p.lower()):
                text = text[len(p) :].strip()
        return text[:100]  # Safe limit

    async def get_trending_topics(self, assistant_id: Optional[UUID] = None, limit: int = 10) -> List[TopicStat]:
        """Fetch trending topics for analytics dashboard."""
        raw_limit = limit * 5
        raw_topics = await self.repository.get_trending(assistant_id, raw_limit)

        aggregated_map: Dict[str, TopicStat] = {}

        for topic in raw_topics:
            key = topic.canonical_text.strip()
            if key in aggregated_map:
                existing = aggregated_map[key]
                existing.frequency += topic.frequency
                if topic.raw_variations:
                    existing.raw_variations.extend(topic.raw_variations)
            else:
                aggregated_map[key] = TopicStat.model_validate(topic)

        unique_topics = list(aggregated_map.values())
        # Filter minimum 2 hits to avoid one-off questions
        unique_topics = [t for t in unique_topics if t.frequency >= 2]
        unique_topics.sort(key=lambda x: x.frequency, reverse=True)
        return unique_topics[:limit]

    async def delete_assistant_topics(self, assistant_id: UUID) -> None:
        """
        Delete all trending topic vectors associated with an assistant.
        Uses VectorRepository for reliable async execution.
        """
        try:
            # We need to clean up all trending collections for this assistant
            # Since we don't necessarily know which providers it used, we try all
            supported_providers = ["gemini", "openai", "local"]
            for p in supported_providers:
                coll = self._get_collection_name(p)
                await self.vector_repo.delete_by_assistant_id(coll, assistant_id)

            logger.info(f"Cleaned up vectors across all trending collections for assistant {assistant_id}")
        except Exception as e:
            logger.error(f"Failed to delete topics for {assistant_id}: {e}")


async def get_trending_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> TrendingService:
    """Dependency Provider."""
    # We construct Repo here to ensure standard DI chain
    vector_repo = VectorRepository(await vector_service.get_async_qdrant_client())

    return TrendingService(
        db=db, vector_service=vector_service, settings_service=settings_service, vector_repository=vector_repo
    )
