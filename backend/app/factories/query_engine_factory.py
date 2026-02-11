import logging
import time
from typing import Annotated, Any, List, Optional

from fastapi import Depends
from llama_index.core import PromptTemplate, Settings
from llama_index.core.query_engine import BaseQueryEngine, RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters

from app.core.exceptions import ConfigurationError
from app.core.prompts import AGENTIC_RESPONSE_PROMPT, AGENTIC_RESPONSE_PROMPT_FR
from app.factories.chat_engine_factory import ChatEngineFactory
from app.schemas.enums import ConnectorType
from app.factories.llm_factory import LLMFactory
from app.services.settings_service import SettingsService
from app.services.sql_discovery_service import SQLDiscoveryService, get_sql_discovery_service
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)


class UnifiedQueryEngineFactory:
    """
    Factory that implements the Agentic Router Architecture.
    Decides dynamically between:
    1. Direct Vector Query Engine (Zero Latency) -> if NO SQL detected.
    2. Router Query Engine (Agentic Decision) -> if SQL IS configured.
    """

    def __init__(self, vector_service: VectorService, sql_service: SQLDiscoveryService):
        self.vector_service = vector_service
        self.sql_service = sql_service

    async def is_configured(self, assistant: Any) -> bool:
        # P0: Debugging "Router Error" - verify why SQL might be triggering
        # For now, let's assume this delegates to the SQL discovery service
        return await self.sql_service.is_configured(assistant)

    def _determine_vector_provider(self, assistant: Any) -> str:
        """Helper to determine correct embedding provider from linked connectors."""
        provider = "gemini"
        logger.info(f"ROUTER_DEBUG | Inspecting Assistant {assistant.id} connectors...")

        if hasattr(assistant, "linked_connectors"):
            providers = set()
            for conn in assistant.linked_connectors:
                # Configuration is a dict (jsonb)
                curr_provider = "gemini"
                if hasattr(conn, "configuration") and conn.configuration:
                    curr_provider = conn.configuration.get("ai_provider", "gemini")

                logger.info(f"ROUTER_DEBUG | Connector {conn.id} ({conn.name}) | Provider: {curr_provider}")
                providers.add(curr_provider)

            if "openai" in providers:
                logger.info("ROUTER_DEBUG | Found 'openai' in providers. Forcing OpenAI.")
                return "openai"
            elif "local" in providers:
                return "local"

        logger.info(f"ROUTER_DEBUG | Defaulting to {provider}")
        return provider

    async def create_engine(self, assistant: Any, language: str = "en", **kwargs) -> BaseQueryEngine:
        """
        Creates the appropriate query engine based on system configuration.
        Implements Strict Routing:
        - SQL Only -> Vanna/NLSQL Engine (No Router)
        - Docs Only -> Vector Engine (No Router)
        - Hybrid -> Router Query Engine
        """
        start_time = time.time()

        # 1. Analyze Resources
        has_sql = await self.sql_service.is_configured(assistant)

        has_docs = False
        if assistant.linked_connectors:
            for conn in assistant.linked_connectors:
                ctype = str(conn.connector_type).lower().strip() if conn.connector_type else ""
                # If it's NOT a SQL connector, we assume it's a document source (file, web, etc.)
                if ctype not in [
                    ConnectorType.SQL.value,
                    ConnectorType.VANNA_SQL.value,
                    "sql",
                    "vanna_sql",
                    "mssql",
                    "postgres",
                ]:
                    has_docs = True
                    break

        logger.info(f"ROUTER_LOGIC | Assistant {assistant.id} | Has SQL: {has_sql} | Has Docs: {has_docs}")

        # 2. Case: SQL Only (Strict Bypass)
        if has_sql and not has_docs:
            logger.info("ROUTER_LOGIC | Mode: SQL ONLY (Bypassing Router)")
            sql_engine = await self.sql_service.get_engine(assistant)
            if sql_engine:
                return sql_engine
            logger.warning("ROUTER_LOGIC | SQL config valid but engine failed. Fallback to Vector (empty).")

        # 3. Initialize Shared Components (LLM, Settings) if needed for Vector/Router
        # Determine Embedding Provider
        provider = self._determine_vector_provider(assistant)

        # Prepare Filters (ACL)
        from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters

        filters = None
        if assistant.linked_connectors:
            # Filter out SQL connectors from vector search if we want to be strict,
            # but usually vector store only contains docs anyway.
            # We just add ACL for ALL linked connectors to be safe.
            connector_filters = [
                MetadataFilter(key="connector_id", value=str(conn.id), operator=FilterOperator.EQ)
                for conn in assistant.linked_connectors
            ]
            filters = MetadataFilters(filters=connector_filters, condition="or")

        # 4. Configure Vector Engine (Base for Docs-only and Router)
        # Inject Language & Instructions
        from llama_index.core import PromptTemplate

        from app.core.prompts import AGENTIC_RESPONSE_PROMPT, AGENTIC_RESPONSE_PROMPT_FR

        if language and "fr" in language.lower():
            selected_prompt = AGENTIC_RESPONSE_PROMPT_FR
        else:
            lang_instruction = f"IMPORTANT: User language is {language}. You MUST answer in {language}.\n\n"
            selected_prompt = lang_instruction + AGENTIC_RESPONSE_PROMPT

        if hasattr(assistant, "instructions") and assistant.instructions:
            selected_prompt = f"{assistant.instructions}\n\n{selected_prompt}"

        settings_service = SettingsService(self.sql_service.db)
        await settings_service.load_cache()

        llm = await ChatEngineFactory.create_from_assistant(assistant, settings_service)

        vector_kwargs = kwargs.copy()
        vector_kwargs["text_qa_template"] = PromptTemplate(selected_prompt)
        vector_kwargs["llm"] = llm  # Pass the LLM to vector engine

        vector_engine = await self.vector_service.get_query_engine(provider=provider, filters=filters, **vector_kwargs)

        # 5. Case: Docs Only (Strict Bypass)
        if has_docs and not has_sql:
            logger.info("ROUTER_LOGIC | Mode: DOCS ONLY (Bypassing Router)")
            return vector_engine

        # 6. Case: Hybrid (Router)
        if has_sql and has_docs:
            logger.info("ROUTER_LOGIC | Mode: HYBRID (Active Router)")

            # Define Tools
            vector_tool = QueryEngineTool(
                query_engine=vector_engine,
                metadata=ToolMetadata(
                    name="transit_docs",
                    description="Use this tool for searching unstructured documents, policies, and text files.",
                ),
            )

            sql_engine = await self.sql_service.get_engine(assistant)
            sql_tool = QueryEngineTool(
                query_engine=sql_engine or vector_engine,  # Fallback
                metadata=ToolMetadata(
                    name="transit_sql_db",
                    description="Use this tool for looking up specific records, IDs, verses, and quantitative data from the database.",
                ),
            )

            # Initialize Router LLM
            # Settings service already loaded above

            # Router Model Selection - Use assistant's configured provider
            router_provider = assistant.model_provider or "gemini"
            router_model = await settings_service.get_value(f"{router_provider}_chat_model")
            router_api_key = None

            if router_provider == "gemini":
                router_api_key = await settings_service.get_value("gemini_api_key")
            elif router_provider == "openai":
                router_api_key = await settings_service.get_value("openai_api_key")
            elif router_provider == "mistral":
                router_api_key = await settings_service.get_value("mistral_api_key")
            elif router_provider == "ollama":
                # For Ollama, we repurpose api_key to hold the Base URL if needed
                router_api_key = await settings_service.get_value("ollama_base_url")

            if not router_model:
                from app.core.exceptions import ConfigurationError

                raise ConfigurationError(f"Router model not configured for provider {router_provider}")

            llm = LLMFactory.create_llm(router_provider, router_model, router_api_key)

            return RouterQueryEngine(
                selector=LLMSingleSelector.from_defaults(llm=llm),
                query_engine_tools=[vector_tool, sql_tool],
                verbose=True,
            )

        # Fallback (Should not be reached usually, defaults to Doc search)
        logger.warning("ROUTER_LOGIC | Fallback to Vector Engine (No clear resources detected)")
        return vector_engine


async def get_query_engine_factory(
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    sql_service: Annotated[SQLDiscoveryService, Depends(get_sql_discovery_service)],
) -> UnifiedQueryEngineFactory:
    return UnifiedQueryEngineFactory(vector_service, sql_service)
