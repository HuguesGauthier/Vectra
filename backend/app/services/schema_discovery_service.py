import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

import aiofiles
from fastapi import Depends
from llama_index.llms.google_genai import GoogleGenAI
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.database import get_db
from app.core.exceptions import ConfigurationError, EntityNotFound, FileSystemError, TechnicalError
from app.core.interfaces.base_connector import get_full_path_from_connector
from app.core.time import SystemClock, TimeProvider
from app.models.enums import DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.services.connector_state_service import ConnectorStateService, get_connector_state_service
from app.services.settings_service import SettingsService, get_settings_service

logger = logging.getLogger(__name__)

PROMPT_SCHEMA_DISCOVERY = """
You are an expert Data Engineer. Analyze the following CSV structure (first 5 rows provided) and generate a 'Smart Indexing Strategy' configuration for a RAG system.

Goal:
1. RENAME headers to clean snake_case.
2. CLASSIFY columns into 3 types:
    - SEMANTIC: Contains descriptive text, specs, notes (Best for Embedding).
    - FILTER_EXACT: Categorical data (Make, Model, Position, ID, Color) (Best for exact match filtering).
    - FILTER_RANGE: Numerical or Date data (Year, Price, Dimensions) - MUST include year columns if present.
3. DETECT SPECIAL LOGIC:
    - Identify if there are "Start Year" and "End Year" columns (e.g. 'year_start', 'year_end').
    - IMPORTANT: If year columns exist, they MUST be included in BOTH 'start_year_col'/'end_year_col' AND 'filter_range_cols'.

Input CSV Header and Data:
{csv_preview}

Output JSON format ONLY (matches IndexingStrategy schema):
{
  "renaming_map": {"Old Name": "new_name"},
  "semantic_cols": ["description", "features"],
  "filter_exact_cols": ["make", "model", "position_id"],
  "filter_range_cols": ["price", "year_start", "year_end"],  // MUST include year columns
  "start_year_col": "year_start",  // or null
  "end_year_col": "year_end",      // or null
  "primary_id_col": "sku"          // or null
}
"""


class TransientIngestionError(Exception):
    pass


class SchemaDiscoveryService:
    def __init__(
        self,
        db: AsyncSession,
        settings_service: SettingsService,
        state_service: ConnectorStateService,
        clock: TimeProvider = None,
    ):
        self.db = db
        self.settings_service = settings_service
        self.state_service = state_service
        self.clock = clock or SystemClock()
        self.doc_repo = DocumentRepository(db)
        self.connector_repo = ConnectorRepository(db)

        # Config
        self.csv_preview_rows = 5
        self.csv_max_size_mb = 10
        self.llm_timeout_seconds = 30
        self.llm_retry_attempts = 3
        self.json_marker = "```json"

    async def analyze_and_map_csv(self, doc_id: UUID) -> None:
        """
        AI-powered CSV schema discovery using Gemini LLM.
        """
        logger.info(f"START | CSV Analysis | {doc_id}")
        doc = None

        try:
            await self.settings_service.load_cache()

            doc = await self.doc_repo.get_by_id(doc_id)
            if not doc:
                raise EntityNotFound(f"Document {doc_id} not found")

            connector = await self.connector_repo.get_by_id(doc.connector_id)
            full_path = get_full_path_from_connector(connector, doc.file_path)

            await self._validate_csv_file(full_path)
            csv_preview = await self._read_csv_preview(full_path)

            api_key = await self.settings_service.get_value("gemini_api_key")

            # P0: Allow fallback to Local/Ollama if Gemini key is missing
            local_extraction_model = await self.settings_service.get_value("local_extraction_model")

            if not api_key and not local_extraction_model:
                raise ConfigurationError("GEMINI_API_KEY missing and no Local Extraction model configured")

            if not api_key:
                api_key = "ollama"  # Signal to use local

            schema_json = await self._discover_schema_with_llm(api_key, csv_preview)

            # Save schema to document metadata
            metadata = dict(doc.file_metadata) if doc.file_metadata else {}
            metadata["ai_schema"] = schema_json

            await self.doc_repo.update(doc.id, {"file_metadata": metadata, "status": DocStatus.INDEXING})
            await self.state_service.update_document_status(doc.id, DocStatus.INDEXING, "Schema discovered.")

            logger.info(f"SUCCESS | CSV Analysis | {doc_id}")

        except (EntityNotFound, ConfigurationError, FileSystemError) as e:
            logger.warning(f"USER_ERROR | {doc_id} | {e}")
            if doc:
                await self.state_service.mark_document_failed(doc.id, str(e))
            raise

        except (asyncio.TimeoutError, TransientIngestionError) as e:
            logger.error(f"TRANSIENT_ERROR | {doc_id} | {e}")
            if doc:
                await self.state_service.mark_document_failed(doc.id, f"LLM error: {e}")
            raise

        except Exception as e:
            logger.critical(f"UNEXPECTED_ERROR | {doc_id} | {e}", exc_info=True)
            if doc:
                await self.state_service.mark_document_failed(doc.id, "Internal error")
            raise

    async def _validate_csv_file(self, path: str) -> None:
        p = Path(path)
        if not await asyncio.to_thread(p.exists):
            raise FileSystemError(f"CSV file not found: {path}")

        size_bytes = (await asyncio.to_thread(p.stat)).st_size
        file_size_mb = size_bytes / (1024**2)
        if file_size_mb > self.csv_max_size_mb:
            raise FileSystemError(f"CSV file too large: {file_size_mb:.1f}MB > {self.csv_max_size_mb}MB limit")

    async def _read_csv_preview(self, path: str) -> str:
        lines = []
        max_lines = self.csv_preview_rows + 1

        async with aiofiles.open(path, mode="r", encoding="utf-8-sig") as f:
            async for line in f:
                lines.append(line)
                if len(lines) >= max_lines:
                    break

        return "".join(lines)

    async def _discover_schema_with_llm(self, api_key: str, csv_preview: str) -> dict:
        gemini_model = await self.settings_service.get_value("gemini_extraction_model")
        local_model = await self.settings_service.get_value("local_extraction_model")

        provider = "gemini"
        model_name = gemini_model
        base_url = None

        # P0: Logic to choose provider
        # If API key is for Gemini (starts with AI...), use Gemini.
        # If API key is "ollama" or empty (handled below), use Local.
        # Ideally, we should pass the provider explicitely.
        # But here `api_key` argument comes from `analyze_and_map_csv` which fetches `gemini_api_key`.
        # We need to refactor `analyze_and_map_csv` to be provider-aware.

        # Quick fix within this method for now, but better to refactor caller.
        # However, let's look at `analyze_and_map_csv`.

        # REFACTORING CALLER LOGIC INLINE HERE FOR SAFETY (Detecting provider from key presence)
        # If the passed `api_key` looks like a Gemini key, use Gemini.
        # If it's missing or we prefer local, use local settings.

        display_key = api_key[:5] if api_key else "None"

        if not api_key or api_key == "ollama":
            provider = "ollama"
            model_name = local_model
            base_url = await self.settings_service.get_value("local_extraction_url")
            api_key = "ollama"  # Dummy for factory

        if not model_name:
            raise ConfigurationError("Extraction model not configured")

        from app.factories.llm_factory import LLMFactory

        llm = LLMFactory.create_llm(
            provider=provider, model_name=model_name, api_key=api_key, temperature=0.0, base_url=base_url
        )

        prompt = PROMPT_SCHEMA_DISCOVERY.replace("{csv_preview}", csv_preview)

        # P0 Fix: Move TransientIngestionError detection into retry decorator
        @retry(
            stop=stop_after_attempt(self.llm_retry_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((asyncio.TimeoutError, TransientIngestionError)),
            reraise=True,
        )
        async def _call_with_retry():
            try:
                response = await asyncio.wait_for(llm.acomplete(prompt), timeout=self.llm_timeout_seconds)
                return response.text
            except asyncio.TimeoutError as e:
                logger.warning("LLM_TIMEOUT | External call timed out")
                raise TransientIngestionError(f"LLM request timed out after {self.llm_timeout_seconds}s") from e

        try:
            response_text = await _call_with_retry()
            return self._parse_llm_response(response_text)
        except TransientIngestionError:
            raise
        except Exception as e:
            logger.error(f"LLM_ERROR | {e}", exc_info=True)
            raise TransientIngestionError(f"LLM API error: {e}") from e

    def _parse_llm_response(self, text: str) -> dict:
        cleaned = text.replace(self.json_marker, "").replace("```", "").strip()
        try:
            schema = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise TechnicalError(f"Failed to parse LLM response as JSON: {e}")

        # Basic Validation for Smart Strategy
        required_keys = ["renaming_map", "semantic_cols"]
        missing = [k for k in required_keys if k not in schema]

        if missing:
            raise TechnicalError(f"LLM response missing required keys: {missing}")

        return schema


async def get_schema_discovery_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    state_service: Annotated[ConnectorStateService, Depends(get_connector_state_service)],
) -> SchemaDiscoveryService:
    return SchemaDiscoveryService(db, settings_service, state_service)
