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
        """Verify if SQL is configured for this assistant."""
        return await self.sql_service.is_configured(assistant)

    def _determine_vector_provider(self, assistant: Any) -> str:
        """Helper to determine correct embedding provider from linked connectors."""
        # Use assistant's own provider as base instead of hardcoding "gemini"
        provider = assistant.model_provider or "ollama"
        logger.debug(f"ROUTER_DEBUG | Inspecting Assistant {assistant.id} connectors...")

        if hasattr(assistant, "linked_connectors"):
            providers = set()
            for conn in assistant.linked_connectors:
                # Configuration is a dict (jsonb)
                # Fallback to the assistant level provider if connector doesn't specify
                curr_provider = provider
                if hasattr(conn, "configuration") and conn.configuration:
                    curr_provider = conn.configuration.get("ai_provider", provider)

                logger.debug(f"ROUTER_DEBUG | Connector {conn.id} ({conn.name}) | Provider: {curr_provider}")
                providers.add(curr_provider)

            if "openai" in providers:
                return "openai"
            elif "local" in providers:
                return "local"
            elif "gemini" in providers:
                return "gemini"
            elif "ollama" in providers:
                return "ollama"

        return provider

    def _is_sql_connector(self, connector_type: Any) -> bool:
        """Robustly detect if a connector type is SQL-based."""
        ctype = str(connector_type).lower().strip() if connector_type else ""
        sql_types = [
            ConnectorType.SQL.value,
            ConnectorType.VANNA_SQL.value,
            "sql",
            "vanna_sql",
            "mssql",
            "postgres",
        ]
        return ctype in sql_types

    async def create_engine(self, assistant: Any, language: str = "en", **kwargs) -> BaseQueryEngine:
        """
        Creates the appropriate query engine based on system configuration.
        Implements Strict Routing:
        - SQL Only -> Vanna/NLSQL Engine (No Router)
        - Docs Only -> Vector Engine (No Router)
        - Hybrid -> Router Query Engine
        """
        # 1. Analyze Resources
        has_sql = await self.sql_service.is_configured(assistant)
        has_docs = False

        if assistant.linked_connectors:
            for conn in assistant.linked_connectors:
                if not self._is_sql_connector(conn.connector_type):
                    has_docs = True
                    break

        logger.info(f"ROUTER_LOGIC | Assistant {assistant.id} | Has SQL: {has_sql} | Has Docs: {has_docs}")

        # 2. Case: SQL Only (Strict Bypass)
        if has_sql and not has_docs:
            logger.info("ROUTER_LOGIC | Mode: SQL ONLY (Bypassing Router)")
            sql_engine = await self.sql_service.get_engine(assistant)
            if sql_engine:
                return sql_engine
            logger.warning("ROUTER_LOGIC | SQL config valid but engine failed. Fallback to Hybrid check.")

        # 3. Initialize Shared Components
        provider = self._determine_vector_provider(assistant)

        # Prepare ACL Filters
        filters = None
        if assistant.linked_connectors:
            connector_filters = [
                MetadataFilter(key="connector_id", value=str(conn.id), operator=FilterOperator.EQ)
                for conn in assistant.linked_connectors
                if not self._is_sql_connector(conn.connector_type)
            ]
            if connector_filters:
                filters = MetadataFilters(filters=connector_filters, condition="or")

        # 4. Configure Prompt & LLM
        if language and "fr" in language.lower():
            selected_prompt = AGENTIC_RESPONSE_PROMPT_FR
        else:
            lang_instruction = f"IMPORTANT: User language is {language}. You MUST answer in {language}.\n\n"
            selected_prompt = lang_instruction + AGENTIC_RESPONSE_PROMPT

        if hasattr(assistant, "instructions") and assistant.instructions:
            selected_prompt = f"{assistant.instructions}\n\n{selected_prompt}"

        # Initialize Services
        settings_service = SettingsService(self.sql_service.db)
        await settings_service.load_cache()

        # Create LLM using existing factory logic (DRY)
        llm = await ChatEngineFactory.create_from_assistant(assistant, settings_service)

        vector_kwargs = kwargs.copy()
        vector_kwargs["text_qa_template"] = PromptTemplate(selected_prompt)
        vector_kwargs["llm"] = llm

        vector_engine = await self.vector_service.get_query_engine(provider=provider, filters=filters, **vector_kwargs)

        # 5. Case: Docs Only (Strict Bypass)
        if has_docs and not has_sql:
            logger.info("ROUTER_LOGIC | Mode: DOCS ONLY (Bypassing Router)")
            return vector_engine

        # 6. Case: Hybrid (Router)
        if has_sql and has_docs:
            logger.info("ROUTER_LOGIC | Mode: HYBRID (Active Router)")

            # Vector Tool
            vector_tool = QueryEngineTool(
                query_engine=vector_engine,
                metadata=ToolMetadata(
                    name="transit_docs",
                    description="Use this tool for searching unstructured documents, policies, and text files.",
                ),
            )

            # SQL Tool
            sql_engine = await self.sql_service.get_engine(assistant)
            sql_tool = QueryEngineTool(
                query_engine=sql_engine or vector_engine,  # Fallback to vector if SQL fails
                metadata=ToolMetadata(
                    name="transit_sql_db",
                    description="Use this tool for looking up specific records, IDs, and quantitative data from the database.",
                ),
            )

            # Create Router LLM using Factory (P1 - DRY)
            router_provider = assistant.model_provider or provider
            router_llm = await ChatEngineFactory.create_from_provider(router_provider, settings_service)

            return RouterQueryEngine(
                selector=LLMSingleSelector.from_defaults(llm=router_llm),
                query_engine_tools=[vector_tool, sql_tool],
                verbose=True,
            )

        # Fallback (Should not be reached usually, defaults to Doc search)
        logger.warning("ROUTER_LOGIC | Fallback to Vector Engine")
        return vector_engine


async def get_query_engine_factory(
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    sql_service: Annotated[SQLDiscoveryService, Depends(get_sql_discovery_service)],
) -> UnifiedQueryEngineFactory:
    return UnifiedQueryEngineFactory(vector_service, sql_service)
