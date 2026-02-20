import logging
import time
from typing import Annotated, Any, Dict, List, Optional

from fastapi import Depends
from llama_index.core import PromptTemplate, Settings
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.callbacks.schema import CBEventType
from llama_index.core.query_engine import BaseQueryEngine, RouterQueryEngine
from llama_index.core.selectors import LLMMultiSelector
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters
from llama_index.core.schema import QueryBundle, QueryType

from app.core.exceptions import ConfigurationError
from app.core.prompts import AGENTIC_RESPONSE_PROMPT, AGENTIC_RESPONSE_PROMPT_FR
from app.factories.chat_engine_factory import ChatEngineFactory
from app.schemas.enums import ConnectorType
from app.factories.llm_factory import LLMFactory
from app.services.settings_service import SettingsService
from app.services.sql_discovery_service import SQLDiscoveryService, get_sql_discovery_service
from app.services.vector_service import VectorService, get_vector_service
from app.services.chat.tool_context import current_tool_name

logger = logging.getLogger(__name__)


class IsolatedQueryEngine(BaseQueryEngine):
    """
    Wrapper ensuring that each tool gets a fresh copy of the QueryBundle.
    Critical for Router setups where tools have different embedding dimensions
    (e.g. Ollama=1024, Gemini=3072). LlamaIndex reuses the bundle by default,
    causing dimension mismatches if the first tool caches its embedding.
    """

    def __init__(
        self,
        engine: BaseQueryEngine,
        tool_metadata: Optional[ToolMetadata] = None,
        display_name: Optional[str] = None,
    ):
        super().__init__(callback_manager=engine.callback_manager)
        self._engine = engine
        self.tool_metadata = tool_metadata
        self.display_name = display_name

    def _query(self, query_bundle: QueryBundle) -> Any:
        # Clone bundle to force re-calculation of embeddings per engine
        new_bundle = QueryBundle(
            query_str=query_bundle.query_str,
            custom_embedding_strs=query_bundle.custom_embedding_strs,
            image_path=query_bundle.image_path,
        )

        if self.display_name or self.tool_metadata:
            # Set ContextVar so callbacks.py can label the RETRIEVE event correctly.
            # We prefer display_name for UI, but fallback to technical tool name.
            label = self.display_name or self.tool_metadata.name
            token = current_tool_name.set(label)
            try:
                with self.callback_manager.event(CBEventType.FUNCTION_CALL, payload={"tool": self.tool_metadata}):
                    return self._engine.query(new_bundle)
            finally:
                current_tool_name.reset(token)

        return self._engine.query(new_bundle)

    async def _aquery(self, query_bundle: QueryBundle) -> Any:
        new_bundle = QueryBundle(
            query_str=query_bundle.query_str,
            custom_embedding_strs=query_bundle.custom_embedding_strs,
            image_path=query_bundle.image_path,
        )

        if self.display_name or self.tool_metadata:
            # ContextVar propagates into child coroutines but NOT into sibling tasks
            # started by asyncio.gather() — exactly what we need for LLMMultiSelector.
            label = self.display_name or self.tool_metadata.name
            token = current_tool_name.set(label)
            try:
                with self.callback_manager.event(CBEventType.FUNCTION_CALL, payload={"tool": self.tool_metadata}):
                    return await self._engine.aquery(new_bundle)
            finally:
                current_tool_name.reset(token)

        return await self._engine.aquery(new_bundle)

    async def aquery(self, str_or_query_bundle: QueryType) -> RESPONSE_TYPE:
        """Async query. Bypasses default event dispatching to avoid duplicates."""
        if isinstance(str_or_query_bundle, str):
            str_or_query_bundle = QueryBundle(str_or_query_bundle)
        return await self._aquery(str_or_query_bundle)

    def query(self, str_or_query_bundle: QueryType) -> RESPONSE_TYPE:
        """Sync query. Bypasses default event dispatching to avoid duplicates."""
        if isinstance(str_or_query_bundle, str):
            str_or_query_bundle = QueryBundle(str_or_query_bundle)
        return self._query(str_or_query_bundle)

    def _get_prompt_modules(self) -> Dict[str, Any]:
        """
        Required by BaseQueryEngine in recent llama-index versions.
        Delegates to the wrapped engine to ensure prompt consistency.
        """
        return {"engine": self._engine}


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

    def _get_active_providers(self, assistant: Any) -> List[str]:
        """Helper to determine all distinct embedding providers from linked connectors."""
        # Use assistant's own provider as base
        base_provider = assistant.model_provider or "ollama"
        providers = set()

        if hasattr(assistant, "linked_connectors") and assistant.linked_connectors:
            for conn in assistant.linked_connectors:
                if not self._is_sql_connector(conn.connector_type):
                    curr_provider = conn.configuration.get("ai_provider", base_provider)
                    providers.add(curr_provider)

        if not providers:
            providers.add(base_provider)

        return list(providers)

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
        active_providers = self._get_active_providers(assistant)
        logger.info(f"ROUTER_LOGIC | Active Providers: {active_providers}")

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

        # Create main LLM
        llm = await ChatEngineFactory.create_from_assistant(assistant, settings_service)

        # 5. Build Vector Tools (One per provider/collection)
        vector_tools = []
        for provider in active_providers:
            # Prepare ACL Filters for this provider's connectors
            provider_filters = None
            if assistant.linked_connectors:
                connector_filters = [
                    MetadataFilter(key="connector_id", value=str(conn.id), operator=FilterOperator.EQ)
                    for conn in assistant.linked_connectors
                    if not self._is_sql_connector(conn.connector_type)
                    and conn.configuration.get("ai_provider") == provider
                ]
                if connector_filters:
                    provider_filters = MetadataFilters(filters=connector_filters, condition="or")

            vector_kwargs = kwargs.copy()
            vector_kwargs["text_qa_template"] = PromptTemplate(selected_prompt)
            vector_kwargs["llm"] = llm

            engine = await self.vector_service.get_query_engine(
                provider=provider, filters=provider_filters, **vector_kwargs
            )

            collection_name = await self.vector_service.get_collection_name(provider)
            tool_metadata = ToolMetadata(
                name=f"vector_search_{provider}",
                description=f"Search in the {provider} knowledge base ({collection_name}). Use this for policies, documents, and general text search.",
            )

            # Determine display name for UI
            is_fr = "fr" in language.lower()
            p_lower = provider.lower() if provider else ""
            
            if p_lower == "ollama":
                display_name = "Recherche Base de Connaissances (Local)" if is_fr else "Knowledge Base Search (Local)"
            elif p_lower == "gemini":
                display_name = "Recherche Base de Connaissances (Gemini)" if is_fr else "Knowledge Base Search (Gemini)"
            else:
                p_label = provider.capitalize() if provider else "Unknown"
                display_name = f"Recherche Base de Connaissances ({p_label})" if is_fr else f"Knowledge Base Search ({p_label})"

            # WRAPPER FIX: Isolate the engine to prevent embedding leakage
            # AND pass metadata so we can emit FUNCTION_CALL events for tracking
            isolated_engine = IsolatedQueryEngine(engine, tool_metadata=tool_metadata, display_name=display_name)

            vector_tools.append(
                QueryEngineTool(
                    query_engine=isolated_engine,
                    metadata=tool_metadata,
                )
            )

        # 6. Case: Docs Only (Strict Bypass if single provider)
        if has_docs and not has_sql:
            if len(vector_tools) == 1:
                logger.info("ROUTER_LOGIC | Mode: DOCS ONLY (Single Provider - Bypassing Router)")
                return vector_tools[0].query_engine
            else:
                logger.info("ROUTER_LOGIC | Mode: DOCS ONLY (Multi Provider - Using Router)")

        # 7. Add SQL Tool if configured
        sql_tool = None
        if has_sql:
            sql_engine = await self.sql_service.get_engine(assistant)
            if sql_engine:
                sql_tool = QueryEngineTool(
                    query_engine=sql_engine,
                    metadata=ToolMetadata(
                        name="sql_analytics",
                        description="Use this tool for looking up structured data, records, IDs, and quantitative analysis from the database.",
                    ),
                )

        # 8. Selection & Return
        if not sql_tool and len(vector_tools) == 1:
            return vector_tools[0].query_engine

        all_tools = vector_tools + ([sql_tool] if sql_tool else [])

        router_provider = assistant.model_provider or (active_providers[0] if active_providers else "ollama")
        router_llm = await ChatEngineFactory.create_from_provider(router_provider, settings_service)

        # CRITICAL: Override LlamaIndex global Settings.llm so LLMMultiSelector
        # doesn't fall back to its OpenAI default for internal components.
        # Scoped locally — this is intentional since we're in an async context
        # (each request gets its own coroutine stack, but Settings is global so
        # we restore it after the engine is built to avoid cross-request pollution).
        from llama_index.core import Settings as LlamaSettings
        # Use _llm (private backing attr) to avoid triggering the property getter
        # which resolves to OpenAI by default if no LLM has been set globally.
        previous_llm = LlamaSettings._llm
        LlamaSettings.llm = router_llm
        try:
            engine = RouterQueryEngine(
                selector=LLMMultiSelector.from_defaults(llm=router_llm),
                query_engine_tools=all_tools,
                verbose=True,
            )
        finally:
            LlamaSettings.llm = previous_llm

        return engine


async def get_query_engine_factory(
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    sql_service: Annotated[SQLDiscoveryService, Depends(get_sql_discovery_service)],
) -> UnifiedQueryEngineFactory:
    return UnifiedQueryEngineFactory(vector_service, sql_service)
