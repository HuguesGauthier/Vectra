import logging
from typing import Annotated, Any, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.settings_service import SettingsService, get_settings_service
from app.services.sql_engine_cache import SQLEngineCache, get_sql_engine_cache

logger = logging.getLogger(__name__)

from datetime import datetime
from uuid import UUID

from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.enums import DocStatus


class SQLDiscoveryService:
    """
    Service responsible for discovering and managing SQL database connections.
    """

    def __init__(self, db: AsyncSession, settings_service: SettingsService, engine_cache: SQLEngineCache = None):
        self.db = db
        self.settings_service = settings_service
        self.engine_cache = engine_cache or get_sql_engine_cache()
        self.connector_repo = ConnectorRepository(db)
        self.document_repo = DocumentRepository(db)

    async def is_configured(self, assistant: Any) -> bool:
        """
        Checks if the Assistant has a valid SQL connection configured.
        Uses a direct DB query to avoid lazy loading issues on detached objects.
        """
        if not assistant or not hasattr(assistant, "id"):
            return False

        try:
            from sqlalchemy import select

            from app.models.assistant import AssistantConnectorLink
            from app.models.connector import Connector
            from app.schemas.enums import ConnectorType

            stmt = (
                select(Connector)
                .join(AssistantConnectorLink, Connector.id == AssistantConnectorLink.connector_id)
                .where(AssistantConnectorLink.assistant_id == assistant.id)
                .where(
                    (Connector.connector_type == ConnectorType.SQL)
                    | (Connector.connector_type == ConnectorType.VANNA_SQL)
                    | (Connector.connector_type == "sql")
                    | (Connector.connector_type == "vanna_sql")
                )
                .limit(1)
            )

            result = await self.db.execute(stmt)
            exists = result.scalar_one_or_none()
            return exists is not None

        except Exception as e:
            logger.error(f"Error checking SQL configuration for assistant {assistant.id}: {e}")
            return False

    def _detect_db_type(self, config: dict) -> tuple[str, bool, str, dict, Optional[int]]:
        """
        Heuristic detection of Database Dialect, Driver, and Port.
        Returns: (dialect_driver, is_mssql, dialect_key, query_params, port)
        """
        host = config.get("host", "")
        port = config.get("port")
        db_type = config.get("type", "").lower()

        # Defaults
        dialect_driver = "postgresql"
        dialect_key = "postgres"
        is_mssql = False
        query_params = {}

        # Heuristic for MSSQL
        if host and ("\\" in host or str(port) == "1433" or db_type in ["mssql", "sqlserver", "sql-server"]):
            is_mssql = True
            dialect_driver = "mssql+pytds"
            dialect_key = "mssql"

            # Port logic for Named Instances vs Default
            if "\\" in host:
                port = None
            elif not port:
                port = 1433

        elif db_type in ["mysql", "mariadb"] or str(port) == "3306":
            dialect_driver = "mysql+pymysql"
            dialect_key = "mysql"
            if not port:
                port = 3306

        return dialect_driver, is_mssql, dialect_key, query_params, port

    async def discover_views(self, connector: Any) -> list[str]:
        """
        Connects to the SQL Database defined in the connector config
        and discovers available views/tables in the target schema.
        """
        import asyncio

        from sqlalchemy import create_engine, inspect
        from sqlalchemy.engine.url import URL

        config = connector.configuration

        # P0 REFACTOR: Use centralized detection
        drivername, is_mssql, _, query_params, port = self._detect_db_type(config)

        url = URL.create(
            drivername=drivername,
            username=config.get("user"),
            password=config.get("password"),
            host=config.get("host"),
            port=port,
            database=config.get("database"),
            query=query_params,
        )

        default_schema = "dbo" if is_mssql else "public"
        schema = config.get("schema", default_schema)

        try:
            # P0: Run blocking inspection in thread
            def _inspect_sync():
                engine = create_engine(url)
                inspector = inspect(engine)
                # Get views and tables
                views = inspector.get_view_names(schema=schema)
                tables = inspector.get_table_names(schema=schema)
                return list(set(views + tables))

            logger.info(
                f"SQL_DISCOVERY | Connecting to {config.get('host')} as {config.get('user')} on DB {config.get('database')} (Schema: {schema})"
            )
            tables = await asyncio.to_thread(_inspect_sync)
            logger.info(f"SQL_DISCOVERY | Inspection Success. Found: {tables}")
            return tables

        except Exception as e:
            logger.error(f"SQL_DISCOVERY | Failed to inspect DB: {e}", exc_info=True)
            return []

    async def test_connection(self, configurationDict: dict) -> bool:
        """
        Tests the connection.
        """
        import asyncio

        from sqlalchemy import create_engine, text
        from sqlalchemy.engine.url import URL

        # P0 REFACTOR: Use centralized detection
        drivername, _, _, query_params, port = self._detect_db_type(configurationDict)

        url = URL.create(
            drivername=drivername,
            username=configurationDict.get("user"),
            password=configurationDict.get("password"),
            host=configurationDict.get("host"),
            port=port,
            database=configurationDict.get("database"),
            query=query_params,
        )

        try:

            def _test_sync():
                engine = create_engine(url)
                # Try a very simple query
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True

            logger.info(f"SQL_TEST_CONNECTION | Testing connection to {configurationDict.get('host')}")
            await asyncio.to_thread(_test_sync)
            logger.info(f"SQL_TEST_CONNECTION | Success")
            return True

        except Exception as e:
            logger.error(f"SQL_TEST_CONNECTION | Failed: {e}")
            raise e

    async def get_view_schema_markdown(self, connector: Any, view_name: str) -> str:
        """
        Generates markdown schema description.
        """
        import asyncio

        from sqlalchemy import create_engine, inspect
        from sqlalchemy.engine.url import URL

        config = connector.configuration

        # P0 REFACTOR: Use centralized detection
        drivername, is_mssql, _, query_params, port = self._detect_db_type(config)

        url = URL.create(
            drivername=drivername,
            username=config.get("user"),
            password=config.get("password"),
            host=config.get("host"),
            port=port,
            database=config.get("database"),
            query=query_params,
        )

        default_schema = "dbo" if is_mssql else "public"
        schema = config.get("schema", default_schema)

        def _get_schema_sync():
            try:
                engine = create_engine(url)
                inspector = inspect(engine)

                columns = inspector.get_columns(view_name, schema=schema)

                md_lines = [f"# Table: {view_name}", "", "## Columns"]
                for col in columns:
                    col_name = col["name"]
                    col_type = col["type"]
                    comment = col.get("comment") or ""
                    md_lines.append(f"- **{col_name}** ({col_type}): {comment}")

                return "\n".join(md_lines)
            except Exception as e:
                logger.error(f"SQL_DISCOVERY | Schema extraction failed for {view_name}: {e}")
                # Return minimal fallback if inspection fails but we know the name
                return f"# Table: {view_name}\n\nSchema info unavailable."

        return await asyncio.to_thread(_get_schema_sync)

    async def discover_vanna_tables(self, connector: Any) -> list[dict]:
        """
        Discovers tables/views for Vanna.
        """
        import asyncio

        from sqlalchemy import create_engine, inspect
        from sqlalchemy.engine.url import URL

        config = connector.configuration

        # P0 REFACTOR: Use centralized detection
        drivername, is_mssql, _, query_params, port = self._detect_db_type(config)

        url = URL.create(
            drivername=drivername,
            username=config.get("user"),
            password=config.get("password"),
            host=config.get("host"),
            port=port,
            database=config.get("database"),
            query=query_params,
        )

        default_schema = "dbo" if is_mssql else "public"
        schema = config.get("schema", default_schema)

        def _discover_sync():
            try:
                engine = create_engine(url)
                inspector = inspect(engine)

                # Get tables and views
                tables = inspector.get_table_names(schema=schema)
                views = inspector.get_view_names(schema=schema)

                results = []

                # Process tables
                for table_name in tables:
                    ddl = self._generate_ddl(inspector, table_name, schema, is_mssql, obj_type="table")
                    results.append(
                        {
                            "name": f"{schema}.{table_name}",
                            "content": ddl,
                            "metadata": {"type": "table", "schema": schema, "trained": False},
                        }
                    )

                # Process views
                for view_name in views:
                    ddl = self._generate_ddl(inspector, view_name, schema, is_mssql, obj_type="view")
                    results.append(
                        {
                            "name": f"{schema}.{view_name}",
                            "content": ddl,
                            "metadata": {"type": "view", "schema": schema, "trained": False},
                        }
                    )

                logger.info(f"VANNA_DISCOVERY | Found {len(tables)} tables and {len(views)} views in schema '{schema}'")
                return results

            except Exception as e:
                logger.error(f"VANNA_DISCOVERY | Failed to discover tables: {e}", exc_info=True)
                return []

        return await asyncio.to_thread(_discover_sync)

    def _generate_ddl(self, inspector, obj_name: str, schema: str, is_mssql: bool, obj_type: str = "table") -> str:
        """
        Generates CREATE TABLE DDL for a given table or view.
        This is a simplified DDL that Vanna can use for training.
        """
        try:
            columns = inspector.get_columns(obj_name, schema=schema)

            # Build CREATE TABLE statement
            create_keyword = "CREATE VIEW" if obj_type == "view" else "CREATE TABLE"
            ddl_lines = [f"{create_keyword} {schema}.{obj_name} ("]

            col_definitions = []
            for col in columns:
                col_name = col["name"]
                col_type = str(col["type"])
                nullable = "" if col.get("nullable", True) else " NOT NULL"
                col_definitions.append(f"    {col_name} {col_type}{nullable}")

            ddl_lines.append(",\n".join(col_definitions))
            ddl_lines.append(");")

            ddl = "\n".join(ddl_lines)

            # Add primary keys if available (tables only)
            if obj_type == "table":
                try:
                    pk_constraint = inspector.get_pk_constraint(obj_name, schema=schema)
                    if pk_constraint and pk_constraint.get("constrained_columns"):
                        pk_cols = ", ".join(pk_constraint["constrained_columns"])
                        ddl += f"\n-- PRIMARY KEY: {pk_cols}"
                except:
                    pass

            return ddl

        except Exception as e:
            logger.error(f"DDL generation failed for {obj_name}: {e}")
            return f"-- DDL generation failed for {schema}.{obj_name}\n-- Error: {str(e)}"

    async def get_engine(self, assistant: Any) -> Any:
        """
        Returns the NLSQLTableQueryEngine for the configured database.
        Uses Persistent Vector Store (Qdrant) for table retrieval (Manual Vectorization).

        Implements caching to avoid expensive engine reconstruction on every query.
        - Cache hit: <100ms (return cached engine)
        - Cache miss: ~5s (build new engine and cache it)
        """
        # 1. Find the SQL Connector to get cache key
        if not assistant or not hasattr(assistant, "id"):
            return None

        try:
            from sqlalchemy import select

            from app.models.assistant import AssistantConnectorLink
            from app.models.connector import Connector
            from app.schemas.enums import ConnectorType

            stmt = (
                select(Connector)
                .join(AssistantConnectorLink, Connector.id == AssistantConnectorLink.connector_id)
                .where(AssistantConnectorLink.assistant_id == assistant.id)
                .where(
                    (Connector.connector_type == ConnectorType.SQL)
                    | (Connector.connector_type == ConnectorType.VANNA_SQL)
                    | (Connector.connector_type == "sql")
                    | (Connector.connector_type == "vanna_sql")
                )
                .limit(1)
            )
            result = await self.db.execute(stmt)
            sql_connector = result.scalar_one_or_none()
        except Exception:
            sql_connector = None

        if not sql_connector:
            return None

        # [UPDATED] UNIFIED SQL STRATEGY: ALWAYS use Vanna Engine
        # Whether it's "sql" (legacy) or "vanna_sql", we now route everything through Vanna
        # for consistent handling of DDL, training, and natural language synthesis.

        # 2. Check cache first
        cached_engine = self.engine_cache.get_engine(assistant.id, sql_connector.id)
        if cached_engine:
            logger.info(f"SQL_ENGINE | Cache Hit for assistant {assistant.id}")
            return cached_engine

        # 3. Build Vanna Engine (Unified)
        logger.info(f"SQL_ENGINE | Unified Strategy: Building Vanna engine for assistant {assistant.id}...")
        engine = await self._build_vanna_engine(assistant, sql_connector)

        # 4. Store in cache
        if engine:
            self.engine_cache.set_engine(assistant.id, sql_connector.id, engine)

        return engine

    async def _build_vanna_engine(self, assistant: Any, vanna_connector: Any) -> Any:
        """
        Creates a Vanna AI query engine wrapper for VANNA_SQL connectors.
        Returns an object that conforms to the BaseQueryEngine interface via duck typing.
        """
        import asyncio

        from app.services.chat.vectra_vanna_service import VannaServiceFactory

        logger.info(f"VANNA_ENGINE | Building Vanna engine for connector {vanna_connector.id}")

        config = vanna_connector.configuration.copy()  # Copy to avoid mutation issues

        # P0 REFACTOR: Explicitly detect DB Type override from heuristics
        _, _, dialect_key, _, _ = self._detect_db_type(config)

        # FORCE the detected dialect into the config passed to Vanna
        # This solves the "generic SQL" config issue
        if not config.get("type") or config.get("type") == "sql":
            logger.info(f"VANNA_ENGINE | Auto-detected dialect: {dialect_key} (overriding generic 'sql')")
            config["type"] = dialect_key

        # Determine Vanna's context provider (might differ from global settings)
        provider = config.get("ai_provider")

        # Create Vanna service instance (Async Factory)
        vanna_svc = await VannaServiceFactory(
            self.settings_service,
            connector_id=vanna_connector.id,
            context_provider=provider,
            connector_config=config,  # Pass the enriched config
        )

        # TODO: Train on DDL if not already trained
        # config = vanna_connector.configuration
        # if config.get("ddl_schema") and not config.get("trained_at"):
        #     await asyncio.to_thread(vanna_svc.train, ddl=config["ddl_schema"])

        # Wrapper class to make Vanna look like a LlamaIndex QueryEngine
        class VannaQueryEngineWrapper:
            def __init__(self, vanna_service, connector_config, settings_service):
                self.vanna = vanna_service
                self.config = connector_config
                self.settings_service = settings_service

            @property
            def callback_manager(self):
                """Expose the LLM's callback manager to allow Agentic Processor to attach handlers."""
                if hasattr(self.vanna, "llm") and self.vanna.llm:
                    return getattr(self.vanna.llm, "callback_manager", None)
                return None

            @callback_manager.setter
            def callback_manager(self, manager):
                """Propagate the callback manager to the underlying LLM."""
                if hasattr(self.vanna, "llm") and self.vanna.llm:
                    self.vanna.llm.callback_manager = manager

            async def aquery(self, query_str: str):
                """Main query method for compatibility with LlamaIndex routers."""
                # Unwrap QueryBundle if needed (LlamaIndex Router passes QueryBundle)
                if hasattr(query_str, "query_str"):
                    query_str = query_str.query_str

                # Extract connection params from config
                conn_params = {
                    "host": self.config.get("host"),
                    "port": self.config.get("port"),
                    "database": self.config.get("database"),
                    "user": self.config.get("user"),
                    "password": self.config.get("password"),
                    "driver": self.config.get("driver", "{ODBC Driver 17 for SQL Server}"),
                }

                logger.info(f"VANNA_QUERY | Submitting question: {query_str}")

                # Call Vanna in thread (it's sync)
                result = await asyncio.to_thread(self.vanna.submit_question, query_str, **conn_params)

                # Convert Vanna result to LlamaIndex-style response
                from llama_index.core.base.response.schema import Response
                from llama_index.core.prompts import PromptTemplate
                from llama_index.core.schema import QueryBundle

                response_text = ""
                sql = result.get("sql", "")
                df = result.get("dataframe")

                logger.info(f"VANNA_QUERY | Result SQL: {sql}")
                logger.info(f"VANNA_QUERY | Dataframe Shape: {df.shape if df is not None else 'None'}")

                # Resolve Language
                lang = await self.settings_service.get_value("app_language", "en")
                is_french = lang == "fr"

                if "error" in result:
                    response_text = f"Error: {result['error']}"
                else:
                    # 1. Synthesize Natural Language Answer
                    if df is not None and not df.empty and self.vanna.llm:
                        try:
                            # Context for LLM
                            data_str = df.to_markdown(index=False)
                            # Truncate if too large
                            if len(data_str) > 4000:
                                data_str = data_str[:4000] + "\n...(truncated)"

                            prompt = (
                                f"User Question: {query_str}\n\n"
                                f"SQL Query: {sql}\n\n"
                                f"Data Results:\n{data_str}\n\n"
                                "Instructions:\n"
                                "1. Answer the user's question explicitly based on the Data Results.\n"
                                "2. If the answer is found, state it clearly.\n"
                                "3. If the data results are not relevant or empty, say 'I found no matching data'.\n"
                                "4. Do NOT simply repeat the question.\n"
                                "5. Be concise."
                            )

                            logger.info("VANNA_QUERY | Synthesizing answer...")

                            # Use Vanna's LLM to generate response
                            if hasattr(self.vanna.llm, "complete"):
                                # If it's a LlamaIndex LLM
                                llm_response = self.vanna.llm.complete(prompt)
                                response_text = str(llm_response)
                            elif hasattr(self.vanna.llm, "submit_prompt"):
                                # If it's a Vanna/Other LLM wrapper
                                response_text = self.vanna.llm.submit_prompt(prompt)
                            else:
                                # Fallback
                                response_text = (
                                    "J'ai trouvé les données ci-dessous." if is_french else "I found the data below."
                                )

                        except Exception as e:
                            logger.error(f"Vanna Synthesis Failed: {e}", exc_info=True)
                            response_text = (
                                "J'ai trouvé les données demandées." if is_french else "I found the requested data."
                            )
                    elif df is not None and df.empty:
                        response_text = (
                            "J'ai exécuté la requête SQL mais elle n'a retourné aucun résultat."
                            if is_french
                            else "I ran the SQL query but it returned no results."
                        )
                    else:
                        response_text = (
                            "J'ai généré le SQL mais j'ai rencontré une erreur d'exécution."
                            if is_french
                            else "I generated the SQL but encountered an execution error."
                        )

                    # 2. Append Technical Details (Markdown) - DISABLED by default
                    # We store it in metadata if needed, but don't clutter the chat
                    # technical_block = f"\n\n<details><summary>Technical Details</summary>\n\n**Generated SQL:**\n```sql\n{sql}\n```\n"
                    # if df is not None:
                    #      technical_block += f"\n**Results:**\n{df.to_markdown(index=False)}\n"
                    # technical_block += "</details>"

                    # response_text += technical_block

                # Metadata for Agentic Processor (Visualization)
                metadata = {}
                if "sql" in result:
                    # Convert DataFrame to dict for JSON serialization if possible
                    df_res = df.to_dict(orient="records") if df is not None and not df.empty else []

                    metadata["sql_query_result"] = df_res
                    metadata["sql"] = result.get("sql")
                    metadata["result"] = df_res  # Fallback key

                    # P0 FIX: Append structured table data for AgenticProcessor to extract
                    # We use :::table JSON ::: format
                    import json

                    if df_res:
                        try:
                            # Ensure we only serialize standard types
                            table_json = json.dumps(df_res, default=str)
                            response_text += f"\n\n:::table{table_json}:::"
                            logger.info("VANNA_QUERY | Appended :::table block for extraction")
                        except Exception as e:
                            logger.error(f"Failed to serialize table data: {e}")

                return Response(response=response_text, metadata=metadata)

            def query(self, query_str: str):
                """Sync query method (calls async internally)."""
                import asyncio

                # Unwrap QueryBundle if needed
                if hasattr(query_str, "query_str"):
                    query_str = query_str.query_str

                # P0 FIX: Use asyncio.run() to creates a new event loop for this thread.
                # asyncio.get_event_loop() fails in threads spawned by to_thread().
                return asyncio.run(self.aquery(query_str))

        return VannaQueryEngineWrapper(vanna_svc, vanna_connector.configuration, self.settings_service)

    async def _build_engine(self, assistant: Any, sql_connector: Any) -> Any:
        """
        Internal method to build a new NLSQLTableQueryEngine.
        Separated from get_engine() to enable caching logic.
        """
        from llama_index.core import Settings, SQLDatabase
        from llama_index.core.query_engine import NLSQLTableQueryEngine
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine.url import URL

        from app.services.chat.utils import LLMFactory
        from app.services.vector_service import VectorService

        # ... (Previous connection logic omitted for brevity, will be kept by context) ...
        # (This replacement targets the END of the function where engine is created and returned)
        # 1. Initialize DB Connection (Engine)
        config = sql_connector.configuration
        host = config.get("host")
        port = config.get("port")

        dialect = "postgresql"
        query_params = {}
        is_mssql = False

        if host and ("\\" in host or str(port) == "1433" or config.get("type") == "mssql"):
            is_mssql = True
            dialect = "mssql+pytds"
            if "\\" in host:
                port = None
            elif not port:
                port = 1433

        url = URL.create(
            drivername=dialect,
            username=config.get("user"),
            password=config.get("password"),
            host=host,
            port=port,
            database=config.get("database"),
            query=query_params,
        )

        default_schema = "dbo" if is_mssql else "public"
        schema = config.get("schema", default_schema)

        engine = create_engine(url)

        # 2. Discover Available Tables (Lightweight Inspection)
        table_names = await self.discover_views(sql_connector)
        if not table_names:
            logger.warning("SQL_DISCOVERY | No tables found in DB.")
            return None

        # 3. Initialize LLM & Embedding
        await self.settings_service.load_cache()
        from app.factories.chat_engine_factory import ChatEngineFactory

        llm = await ChatEngineFactory.create_from_assistant(assistant, self.settings_service)

        embed_provider = await self.settings_service.get_value("embedding_provider")
        if not embed_provider:
            logger.warning("embedding_provider not configured, using 'gemini' as fallback")
            embed_provider = "gemini"
        vector_service = VectorService(self.settings_service)
        embed_model = await vector_service.get_embedding_model(provider=embed_provider)

        Settings.embed_model = embed_model
        Settings.llm = llm

        # 4. Persistent Retriever (Qdrant)
        # ... (Retriever definitions omitted, assuming they are defined above or we use existing) ...
        # Ideally, we should reuse the classes if they are in scope or defined outside.
        # Since they are inside _build_engine in the original code, we need to keep them or move them.
        # For this edit, I will assume I am replacing the WHOLE _build_engine body or effectively managing context.
        # But wait, looking at the previous view_file, the classes `PersistentVectorTableRetriever` etc are INSIDE _build_engine.
        # So I need to be careful not to delete them.

        # Strategy: I will use `view_file` again to get the full content of _build_engine to be safe,
        # or I will target only the return statement if possible.
        # But the classes need to be instantiated.

        # Let's wrap the return value.

        # ... (Existing Retriever Logic) ...
        # (I'll assume the retriever logic is correct and just modify the return part)

        # BUT I cannot target just the return without context of local variables.
        # So I will re-implement the wrapper logic at the end.

        # Fix: I'll use a `read_file` to capture the whole function and rewrite it carefully.
        # Given I cannot see lines 600+, I shouldn't blindly replace.
        # I will READ MORE lines first.
        pass
        """
        Internal method to build a new NLSQLTableQueryEngine.
        Separated from get_engine() to enable caching logic.
        """
        from llama_index.core import Settings, SQLDatabase
        from llama_index.core.query_engine import NLSQLTableQueryEngine
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine.url import URL

        from app.services.chat.utils import LLMFactory
        from app.services.vector_service import VectorService

        # 1. Initialize DB Connection (Engine)
        config = sql_connector.configuration
        host = config.get("host")
        port = config.get("port")

        dialect = "postgresql"
        query_params = {}
        is_mssql = False

        if host and ("\\" in host or str(port) == "1433" or config.get("type") == "mssql"):
            is_mssql = True
            dialect = "mssql+pytds"
            if "\\" in host:
                port = None
            elif not port:
                port = 1433

        url = URL.create(
            drivername=dialect,
            username=config.get("user"),
            password=config.get("password"),
            host=host,
            port=port,
            database=config.get("database"),
            query=query_params,
        )

        default_schema = "dbo" if is_mssql else "public"
        schema = config.get("schema", default_schema)

        engine = create_engine(url)

        # 2. Discover Available Tables (Lightweight Inspection)
        # We still need the list of valid tables for SQLDatabase validation
        table_names = await self.discover_views(sql_connector)
        if not table_names:
            logger.warning("SQL_DISCOVERY | No tables found in DB.")
            return None

        # 3. Initialize LLM & Embedding
        await self.settings_service.load_cache()

        # Use Factory to respect Assistant's configuration
        from app.factories.chat_engine_factory import ChatEngineFactory

        llm = await ChatEngineFactory.create_from_assistant(assistant, self.settings_service)

        # Initialize Embedding
        embed_provider = await self.settings_service.get_value("embedding_provider")
        if not embed_provider:
            logger.warning("embedding_provider not configured, using 'gemini' as fallback")
            embed_provider = "gemini"
        vector_service = VectorService(self.settings_service)
        embed_model = await vector_service.get_embedding_model(provider=embed_provider)

        Settings.embed_model = embed_model
        Settings.llm = llm

        # 4. Persistent Retriever (Qdrant)
        # Instead of building an index on the fly, we use the one populated by manual scanning

        # Helper Class for Custom Retrieval
        from llama_index.core.objects import SQLTableSchema
        from llama_index.core.retrievers import BaseRetriever
        from llama_index.core.schema import (NodeWithScore, QueryBundle,
                                             TextNode)
        from qdrant_client.http import models as qmodels

        class PersistentVectorTableRetriever(BaseRetriever):
            def __init__(self, vector_service, connector_id, available_tables, collection_name):
                super().__init__()
                self.vector_service = vector_service
                self.connector_id = str(connector_id)
                self.available_tables = set(available_tables)
                self.collection_name = collection_name

            def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
                # Use synchronous execution to avoid asyncio loop conflicts
                # 1. Generate embedding synchronously
                query_vector = embed_model.get_query_embedding(query_bundle.query_str)

                # 3. Search using Synchronous Client
                client = self.vector_service.get_qdrant_client()

                logger.info(
                    f"SQL_DISCOVERY | Searching Qdrant (Sync). Collection: {self.collection_name}, Connector: {self.connector_id}, Query: {query_bundle.query_str}"
                )

                result = client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=5,
                    query_filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="connector_id", match=qmodels.MatchValue(value=self.connector_id)
                            ),
                            # STRICT FILTER: Only return manually vectorized views (Tag: sql_view_schema)
                            qmodels.FieldCondition(key="type", match=qmodels.MatchValue(value="sql_view_schema")),
                        ]
                    ),
                )
                points = result.points if hasattr(result, "points") else result
                logger.info(f"SQL_DISCOVERY | Found {len(points)} points.")

                results = []
                for point in points:
                    payload = point.payload or {}
                    table_name = payload.get("file_name")
                    logger.info(f"SQL_DISCOVERY | Point Found: Table={table_name}")

                    # Relaxed check: Trust vector store if connector matches
                    if table_name:
                        # 4. Anti-Hallucination: Prepend strict constraint
                        base_desc = payload.get("content", f"Table {table_name}")
                        strict_context = (
                            f"IMPORTANT: The ONLY available table matches strict name `{table_name}`.\n"
                            f"Always use `{table_name}` in your FROM clause.\n"
                            f"{base_desc}"
                        )
                        # Fix: Return TextNode instead of SQLTableSchema for BaseRetriever compatibility
                        node = TextNode(text=strict_context, metadata={"table_name": table_name})
                        results.append(NodeWithScore(node=node, score=point.score))

                return results

            async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
                # 1. Generate embedding asynchronously
                query_vector = await embed_model.aget_query_embedding(query_bundle.query_str)

                # 2. Get Async Client
                client = self.vector_service.get_async_qdrant_client()

                logger.info(
                    f"SQL_DISCOVERY | Searching Qdrant (Async). Collection: {self.collection_name}, Connector: {self.connector_id}, Query: {query_bundle.query_str}"
                )

                # 3. Search asynchronously
                result = await client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=5,
                    query_filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="connector_id", match=qmodels.MatchValue(value=self.connector_id)
                            ),
                            qmodels.FieldCondition(key="type", match=qmodels.MatchValue(value="sql_view_schema")),
                        ]
                    ),
                )
                points = result.points if hasattr(result, "points") else result
                logger.info(f"SQL_DISCOVERY | Found {len(points)} points (Async).")

                results = []
                for point in points:
                    payload = point.payload or {}
                    table_name = payload.get("file_name")
                    logger.info(f"SQL_DISCOVERY | Point Found (Async): Table={table_name}")

                    # Relaxed check: Trust vector store if connector matches
                    if table_name:
                        # 4. Anti-Hallucination: Prepend strict constraint
                        base_desc = payload.get("content", f"Table {table_name}")
                        strict_context = (
                            f"IMPORTANT: The ONLY available table matches strict name `{table_name}`.\n"
                            f"Always use `{table_name}` in your FROM clause.\n"
                            f"DO NOT use prefixes like `vectra.{table_name}` or `dbo.{table_name}`.\n\n"
                            f"{base_desc}"
                        )
                        # Fix: Return TextNode instead of SQLTableSchema for BaseRetriever compatibility
                        node = TextNode(text=strict_context, metadata={"table_name": table_name})
                        results.append(NodeWithScore(node=node, score=point.score))

                return results

        # 5. Adapter to return Objects instead of Nodes
        # NLSQLTableQueryEngine requires an ObjectRetriever (returns list[SQLTableSchema])
        from llama_index.core.objects import ObjectRetriever

        class VectorObjectRetriever(ObjectRetriever):
            def __init__(self, vector_retriever):
                self._vector_retriever = vector_retriever

            def retrieve(self, query_bundle: QueryBundle) -> list[SQLTableSchema]:
                nodes = self._vector_retriever.retrieve(query_bundle)
                # Convert TextNodes back to SQLTableSchema
                schemas = []
                for n in nodes:
                    table_name = n.node.metadata.get("table_name")
                    if table_name:
                        schemas.append(SQLTableSchema(table_name=table_name, context_str=n.node.get_content()))
                return schemas

            async def aretrieve(self, query_bundle: QueryBundle) -> list[SQLTableSchema]:
                nodes = await self._vector_retriever.aretrieve(query_bundle)
                schemas = []
                for n in nodes:
                    table_name = n.node.metadata.get("table_name")
                    if table_name:
                        schemas.append(SQLTableSchema(table_name=table_name, context_str=n.node.get_content()))
                return schemas

        collection_name = await vector_service.get_collection_name(embed_provider)

        vector_retriever = PersistentVectorTableRetriever(
            vector_service, sql_connector.id, table_names, collection_name
        )
        object_retriever = VectorObjectRetriever(vector_retriever)

        sql_database = SQLDatabase(engine, schema=schema, include_tables=table_names, view_support=True)

        # Create custom text-to-SQL prompt with Canadian dollar currency instructions
        from llama_index.core.prompts import PromptTemplate
        from llama_index.core.prompts.prompt_type import PromptType

        CUSTOM_TEXT_TO_SQL_TMPL = (
            "Given an input question, first create a syntactically correct {dialect} "
            "query to run, then look at the results of the query and return the answer. "
            "You can order the results by a relevant column to return the most "
            "interesting examples in the database.\n\n"
            "Never query for all the columns from a specific table, only ask for a "
            "few relevant columns given the question.\n\n"
            "Pay attention to use only the column names that you can see in the schema "
            "description. "
            "Be careful to not query for columns that do not exist. "
            "Pay attention to which column is in which table. "
            "Also, qualify column names with the table name when needed. "
            "\n\n"
            "IMPORTANT - Currency Formatting:\n"
            "All monetary amounts MUST be displayed in Canadian dollars.\n"
            "Use the symbol $ (NEVER €, £, or other currencies).\n"
            "Format: XX XXX $ or XX XXX,XX $ (with spaces as thousand separators).\n"
            "Example: 4 000 $ or 3 500,50 $\n"
            "\n\n"
            "You are required to use the following format, each taking one line:\n\n"
            "Question: Question here\n"
            "SQLQuery: SQL Query to run\n"
            "SQLResult: Result of the SQLQuery\n"
            "Answer: Final answer here\n\n"
            "Only use tables listed below.\n"
            "{schema}\n\n"
            "Question: {query_str}\n"
            "SQLQuery: "
        )

        custom_text_to_sql_prompt = PromptTemplate(
            CUSTOM_TEXT_TO_SQL_TMPL,
            prompt_type=PromptType.TEXT_TO_SQL,
        )

        # CRITICAL: Also customize the response synthesis prompt (this generates the final text)
        CUSTOM_RESPONSE_SYNTHESIS_TMPL = (
            "Given an input question, synthesize a response from the query results.\n"
            "\n"
            "IMPORTANT - Currency Formatting:\n"
            "All monetary amounts MUST be displayed in Canadian dollars.\n"
            "Use the symbol $ (NEVER €, £, or other currencies).\n"
            "Format: XX XXX $ or XX XXX,XX $ (with spaces as thousand separators).\n"
            "Example: 4 000 $ NOT 4 000 € or 4000$\n"
            "\n"
            "Query: {query_str}\n"
            "SQL: {sql_query}\n"
            "SQL Response: {context_str}\n"
            "Response: "
        )

        custom_response_synthesis_prompt = PromptTemplate(
            CUSTOM_RESPONSE_SYNTHESIS_TMPL,
            prompt_type=PromptType.SQL_RESPONSE_SYNTHESIS_V2,
        )

        # 6. Wrapper for Standard SQL to match Vanna Formatting
        class StandardQueryEngineWrapper:
            def __init__(self, nl_sql_engine):
                self.engine = nl_sql_engine

            @property
            def callback_manager(self):
                return self.engine.callback_manager

            @callback_manager.setter
            def callback_manager(self, manager):
                self.engine.callback_manager = manager

            async def aquery(self, query_str):
                # Execute Standard LlamaIndex Query
                response = await self.engine.aquery(query_str)

                # Extract Metadata
                sql = response.metadata.get("sql_query", "")
                results = response.metadata.get("result", [])

                # Try to synthesize better answer if empty
                # Inspect response.response (default synthesis might be generic)

                # Helper to convert results to dataframe-like markdown
                import pandas as pd

                df = None
                if results and isinstance(results, list):
                    df = pd.DataFrame(results)

                new_response_text = response.response

                # Force "No Results" message if data is empty
                if not results or (df is not None and df.empty):
                    new_response_text = "I ran the SQL query but it returned no results. This might be due to a mismatch in names (e.g. 'Gen' vs 'Gn')."

                # Append Technical Details
                technical_block = (
                    f"\n\n<details><summary>Technical Details</summary>\n\n**Generated SQL:**\n```sql\n{sql}\n```\n"
                )
                if df is not None and not df.empty:
                    technical_block += f"\n**Results:**\n{df.to_markdown(index=False)}\n"
                technical_block += "</details>"

                # If Technical Details already present (unlikely in standard), don't double add
                if "Technical Details" not in new_response_text:
                    new_response_text += technical_block

                # Update response text
                response.response = new_response_text

                # Ensure Metadata is compatible with AgenticProcessor
                if "sql_query_result" not in response.metadata:
                    response.metadata["sql_query_result"] = results

                return response

            def query(self, query_str):
                import asyncio

                return asyncio.run(self.aquery(query_str))

        inner_engine = NLSQLTableQueryEngine(
            sql_database=sql_database,
            table_retriever=object_retriever,
            llm=llm,
            text_to_sql_prompt=custom_text_to_sql_prompt,  # For SQL generation
            response_synthesis_prompt=custom_response_synthesis_prompt,  # For final text
            streaming=True,
        )

        return StandardQueryEngineWrapper(inner_engine)

    async def scan_and_persist_views(self, connector_id: UUID) -> dict:
        """
        Discovers views and syncs them as Documents in the DB.
        """
        from app.core.connection_manager import manager
        from app.schemas.connector import ConnectorResponse

        logger.info(f"SQL_SCAN | Starting scan for {connector_id}")

        # Removed invalid call to emit_dashboard_update

        # 1. Fetch Connector
        connector = await self.connector_repo.get_by_id(connector_id)
        if not connector:
            raise ValueError("Connector not found")

        # 2. Discover payload (Views/Tables)
        # Branch based on connector type
        if connector.connector_type == "vanna_sql":
            # For Vanna SQL: Discover tables/views with full DDL
            table_objects = await self.discover_vanna_tables(connector)
            logger.info(f"VANNA_SCAN | Found {len(table_objects)} tables/views with DDL")

            # 3. Fetch existing docs
            existing_docs = await self.document_repo.get_by_connector(connector_id)
            existing_map = {doc.file_path: doc for doc in existing_docs}

            # 4. Sync Logic
            to_create = []
            to_update = []
            to_delete_ids = []

            found_objects = {obj["name"] for obj in table_objects}

            # Create or Update
            # Create or Update
            for obj in table_objects:
                obj_name = obj["name"]

                # Enrich metadata with DDL
                metadata = obj["metadata"]
                metadata["ddl"] = obj["content"]

                if obj_name not in existing_map:
                    # Create new document
                    to_create.append(
                        {
                            "connector_id": connector_id,
                            "file_path": obj_name,
                            "file_name": obj_name,
                            # "content": obj['content'],  <-- REMOVED: Model has no content field
                            "file_size": len(obj["content"]),
                            "status": DocStatus.PENDING,
                            "file_metadata": metadata,
                        }
                    )
                else:
                    # Update existing if DDL changed
                    existing_doc = existing_map[obj_name]
                    existing_metadata = existing_doc.file_metadata or {}

                    if existing_metadata.get("ddl") != obj["content"]:
                        to_update.append(
                            {
                                "id": existing_doc.id,
                                # "content": obj['content'], <-- REMOVED
                                "file_size": len(obj["content"]),
                                "file_metadata": metadata,
                            }
                        )

            # Delete (Objects removed from DB)
            for path, doc in existing_map.items():
                if path not in found_objects:
                    to_delete_ids.append(doc.id)

            # 5. Commit
            if to_create:
                await self.document_repo.create_batch(to_create)
            if to_update:
                for update_data in to_update:
                    doc_id = update_data.pop("id")
                    await self.document_repo.update(doc_id, update_data)
            if to_delete_ids:
                # 🔴 P0: Cleanup Orphaned Vectors
                try:
                    from app.repositories.vector_repository import \
                        VectorRepository
                    from app.services.vector_service import VectorService

                    # Initialize Vector Service
                    vector_svc = VectorService(self.settings_service)
                    client = vector_svc.get_async_qdrant_client()
                    vector_repo = VectorRepository(client)

                    # Determine collection (using current connector config)
                    provider = connector.configuration.get("ai_provider", "gemini")
                    collection_name = await vector_svc.get_collection_name(provider)

                    await vector_repo.delete_by_document_ids(collection_name, to_delete_ids)
                    logger.info(f"SQL_SCAN | Cleaned up vectors for {len(to_delete_ids)} deleted documents")
                except Exception as e:
                    logger.error(f"SQL_SCAN | Failed to cleanup vectors: {e}")

                await self.document_repo.delete_batch(to_delete_ids)

            await self.db.commit()

            stats = {"added": len(to_create), "deleted": len(to_delete_ids), "updated": len(to_update)}

        else:
            # For regular SQL: Discover view names only (original logic)
            views = await self.discover_views(connector)
            logger.info(f"SQL_SCAN | Found {len(views)} views/tables")

            # 3. Fetch existing docs
            existing_docs = await self.document_repo.get_by_connector(connector_id)
            existing_map = {doc.file_path: doc for doc in existing_docs}

            # 4. Sync Logic (Simple: View Name = file_path)
            to_create = []
            to_delete_ids = []

            found_views = set(views)

            # Create
            for view in views:
                if view not in existing_map:
                    to_create.append(
                        {
                            "connector_id": connector_id,
                            "file_path": view,
                            "file_name": view,
                            "file_size": 0,
                            "status": DocStatus.PENDING,
                            "file_metadata": {"type": "view", "source": "sql_discovery"},
                        }
                    )

            # Delete (Views removed from DB)
            for path, doc in existing_map.items():
                if path not in found_views:
                    to_delete_ids.append(doc.id)

            # 5. Commit
            if to_create:
                await self.document_repo.create_batch(to_create)
            if to_delete_ids:
                await self.document_repo.delete_batch(to_delete_ids)

            await self.db.commit()

            stats = {"added": len(to_create), "deleted": len(to_delete_ids), "updated": 0}

        # Update Connector Stats
        total = await self.document_repo.count_by_connector(connector_id)
        updated_c = await self.connector_repo.update(connector_id, {"total_docs_count": total})

        # Emit update
        resp = ConnectorResponse.model_validate(updated_c)
        await manager.emit_connector_updated(resp.model_dump(mode="json"))

        return stats


async def get_sql_discovery_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SQLDiscoveryService:
    return SQLDiscoveryService(db, settings_service)
