import asyncio
import json
import logging
from typing import Annotated, Any, Optional
from uuid import UUID

import pandas as pd
from fastapi import Depends
from llama_index.core.base.response.schema import Response
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.core.database import get_db
from app.models.assistant import AssistantConnectorLink
from app.models.connector import Connector
from app.schemas.enums import ConnectorType, DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.connector import ConnectorResponse
from app.services.chat.vanna_services import VannaServiceFactory
from app.services.settings_service import SettingsService, get_settings_service
from app.services.sql_engine_cache import SQLEngineCache, get_sql_engine_cache
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class VannaQueryEngineWrapper:
    """
    Wrapper class to make Vanna look like a LlamaIndex QueryEngine.
    Returns an object that conforms to the BaseQueryEngine interface via duck typing.
    """

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

        sql = result.get("sql", "")
        df = result.get("dataframe")

        logger.info(f"VANNA_QUERY | Result SQL: {sql}")
        logger.info(f"VANNA_QUERY | Dataframe Shape: {df.shape if df is not None else 'None'}")

        # Resolve Language
        lang = await self.settings_service.get_value("app_language", "en")
        is_french = lang == "fr"

        response_text = ""
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
                        llm_response = self.vanna.llm.complete(prompt)
                        response_text = str(llm_response)
                    elif hasattr(self.vanna.llm, "submit_prompt"):
                        response_text = self.vanna.llm.submit_prompt(prompt)
                    else:
                        response_text = (
                            "J'ai trouvé les données ci-dessous." if is_french else "I found the data below."
                        )
                except Exception as e:
                    logger.error(f"Vanna Synthesis Failed: {e}", exc_info=True)
                    response_text = "J'ai trouvé les données demandées." if is_french else "I found the requested data."
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

            # Metadata for Agentic Processor (Visualization)
            metadata = {}
            if "sql" in result:
                # Convert DataFrame to dict for JSON serialization
                df_res = df.to_dict(orient="records") if df is not None and not df.empty else []

                metadata["sql_query_result"] = df_res
                metadata["sql"] = result.get("sql")
                metadata["result"] = df_res

                # [Pragmatic Fix] Append structured table data for AgenticProcessor
                if df_res:
                    try:
                        table_json = json.dumps(df_res, default=str)
                        response_text += f"\n\n:::table{table_json}:::"
                        logger.info("VANNA_QUERY | Appended :::table block")
                    except Exception as e:
                        logger.error(f"Failed to serialize table data: {e}")

            return Response(response=response_text, metadata=metadata)

    def query(self, query_str: str):
        """Sync query method (calls async internally)."""
        # Unwrap QueryBundle if needed
        if hasattr(query_str, "query_str"):
            query_str = query_str.query_str

        # Safe async/sync bridge
        try:
            return asyncio.run(self.aquery(query_str))
        except RuntimeError:
            # Fallback if loop is already running in this thread
            import nest_asyncio

            nest_asyncio.apply()
            return asyncio.run(self.aquery(query_str))


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
        """
        if not assistant or not hasattr(assistant, "id"):
            return False

        try:
            stmt = (
                select(Connector)
                .join(AssistantConnectorLink, Connector.id == AssistantConnectorLink.connector_id)
                .where(AssistantConnectorLink.assistant_id == assistant.id)
                .where(Connector.connector_type.in_([ConnectorType.SQL, ConnectorType.VANNA_SQL, "sql", "vanna_sql"]))
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
        config = connector.configuration
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

            def _inspect_sync():
                engine = create_engine(url)
                inspector = inspect(engine)
                views = inspector.get_view_names(schema=schema)
                tables = inspector.get_table_names(schema=schema)
                return list(set(views + tables))

            logger.info(f"SQL_DISCOVERY | Inspecting DB {config.get('host')} (Schema: {schema})")
            tables = await asyncio.to_thread(_inspect_sync)
            return tables

        except Exception as e:
            logger.error(f"SQL_DISCOVERY | Failed to inspect DB: {e}", exc_info=True)
            return []

    async def test_connection(self, configurationDict: dict) -> bool:
        """Tests the connection."""
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
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True

            await asyncio.to_thread(_test_sync)
            return True
        except Exception as e:
            logger.error(f"SQL_TEST_CONNECTION | Failed: {e}")
            raise

    async def get_view_schema_markdown(self, connector: Any, view_name: str) -> str:
        """Generates markdown schema description."""
        config = connector.configuration
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
                    md_lines.append(f"- **{col['name']}** ({col['type']}): {col.get('comment') or ''}")
                return "\n".join(md_lines)
            except Exception as e:
                logger.error(f"SQL_DISCOVERY | Schema extraction failed for {view_name}: {e}")
                return f"# Table: {view_name}\n\nSchema info unavailable."

        return await asyncio.to_thread(_get_schema_sync)

    async def discover_vanna_tables(self, connector: Any) -> list[dict]:
        """Discovers tables/views for Vanna with full DDL."""
        config = connector.configuration
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
                tables = inspector.get_table_names(schema=schema)
                views = inspector.get_view_names(schema=schema)
                results = []
                for name in tables:
                    ddl = self._generate_ddl(inspector, name, schema, is_mssql, "table")
                    results.append(
                        {
                            "name": f"{schema}.{name}",
                            "content": ddl,
                            "metadata": {"type": "table", "schema": schema, "trained": False},
                        }
                    )
                for name in views:
                    ddl = self._generate_ddl(inspector, name, schema, is_mssql, "view")
                    results.append(
                        {
                            "name": f"{schema}.{name}",
                            "content": ddl,
                            "metadata": {"type": "view", "schema": schema, "trained": False},
                        }
                    )
                return results
            except Exception as e:
                logger.error(f"VANNA_DISCOVERY | Failed: {e}", exc_info=True)
                return []

        return await asyncio.to_thread(_discover_sync)

    def _generate_ddl(self, inspector, obj_name: str, schema: str, is_mssql: bool, obj_type: str = "table") -> str:
        """Generates simplified CREATE TABLE/VIEW DDL for Vanna training."""
        try:
            columns = inspector.get_columns(obj_name, schema=schema)
            create_keyword = "CREATE VIEW" if obj_type == "view" else "CREATE TABLE"
            ddl_lines = [f"{create_keyword} {schema}.{obj_name} ("]
            col_definitions = []
            for col in columns:
                nullable = "" if col.get("nullable", True) else " NOT NULL"
                col_definitions.append(f"    {col['name']} {str(col['type'])}{nullable}")
            ddl_lines.append(",\n".join(col_definitions))
            ddl_lines.append(");")
            ddl = "\n".join(ddl_lines)
            if obj_type == "table":
                try:
                    pk = inspector.get_pk_constraint(obj_name, schema=schema)
                    if pk and pk.get("constrained_columns"):
                        ddl += f"\n-- PRIMARY KEY: {', '.join(pk['constrained_columns'])}"
                except:
                    pass
            return ddl
        except Exception as e:
            logger.error(f"DDL generation failed for {obj_name}: {e}")
            return f"-- DDL generation failed for {schema}.{obj_name}\n-- Error: {str(e)}"

    async def get_engine(self, assistant: Any) -> Any:
        """
        Returns the NLSQLTableQueryEngine for the configured database.
        Always routes through Vanna for consistency.
        """
        if not assistant or not hasattr(assistant, "id"):
            return None

        try:
            stmt = (
                select(Connector)
                .join(AssistantConnectorLink, Connector.id == AssistantConnectorLink.connector_id)
                .where(AssistantConnectorLink.assistant_id == assistant.id)
                .where(Connector.connector_type.in_([ConnectorType.SQL, ConnectorType.VANNA_SQL, "sql", "vanna_sql"]))
                .limit(1)
            )
            result = await self.db.execute(stmt)
            sql_connector = result.scalar_one_or_none()
        except:
            sql_connector = None

        if not sql_connector:
            return None

        # Check cache
        cached_engine = self.engine_cache.get_engine(assistant.id, sql_connector.id)
        if cached_engine:
            return cached_engine

        # Unified Strategy: Always build Vanna Engine
        engine = await self._build_vanna_engine(assistant, sql_connector)

        if engine:
            self.engine_cache.set_engine(assistant.id, sql_connector.id, engine)

        return engine

    async def _build_vanna_engine(self, assistant: Any, vanna_connector: Any) -> Any:
        """Creates a Vanna AI query engine wrapper."""
        config = vanna_connector.configuration.copy()
        _, _, dialect_key, _, _ = self._detect_db_type(config)
        if not config.get("type") or config.get("type") == "sql":
            config["type"] = dialect_key

        vanna_svc = await VannaServiceFactory(
            self.settings_service,
            connector_id=vanna_connector.id,
            context_provider=config.get("ai_provider"),
            connector_config=config,
        )
        return VannaQueryEngineWrapper(vanna_svc, config, self.settings_service)

    async def scan_and_persist_views(self, connector_id: UUID) -> dict:
        """Discovers views and syncs them as Documents in the DB."""
        connector = await self.connector_repo.get_by_id(connector_id)
        if not connector:
            raise ValueError("Connector not found")

        is_vanna = connector.connector_type in [ConnectorType.VANNA_SQL, "vanna_sql"]

        if is_vanna:
            table_objects = await self.discover_vanna_tables(connector)
            existing_docs = await self.document_repo.get_by_connector(connector_id)
            existing_map = {doc.file_path: doc for doc in existing_docs}

            to_create, to_update, to_delete_ids = [], [], []
            found_objects = {obj["name"] for obj in table_objects}

            for obj in table_objects:
                obj_name, metadata = obj["name"], obj["metadata"]
                metadata["ddl"] = obj["content"]
                if obj_name not in existing_map:
                    to_create.append(
                        {
                            "connector_id": connector_id,
                            "file_path": obj_name,
                            "file_name": obj_name,
                            "file_size": len(obj["content"]),
                            "status": DocStatus.IDLE,
                            "file_metadata": metadata,
                        }
                    )
                else:
                    existing_doc = existing_map[obj_name]
                    if (existing_doc.file_metadata or {}).get("ddl") != obj["content"]:
                        to_update.append(
                            {
                                "id": existing_doc.id,
                                "file_size": len(obj["content"]),
                                "file_metadata": metadata,
                            }
                        )

            for path, doc in existing_map.items():
                if path not in found_objects:
                    to_delete_ids.append(doc.id)

            if to_create:
                await self.document_repo.create_batch(to_create)
            if to_update:
                for u in to_update:
                    doc_id = u.pop("id")
                    await self.document_repo.update(doc_id, u)
            if to_delete_ids:
                try:
                    vector_svc = VectorService(self.settings_service)
                    vector_repo = VectorRepository(vector_svc.get_async_qdrant_client())
                    collection = await vector_svc.get_collection_name(
                        connector.configuration.get("ai_provider", "gemini")
                    )
                    await vector_repo.delete_by_document_ids(collection, to_delete_ids)
                except Exception as e:
                    logger.error(f"SQL_SCAN | Vector cleanup failed: {e}")
                await self.document_repo.delete_batch(to_delete_ids)
            await self.db.commit()
            stats = {"added": len(to_create), "deleted": len(to_delete_ids), "updated": len(to_update)}
        else:
            views = await self.discover_views(connector)
            existing_docs = await self.document_repo.get_by_connector(connector_id)
            existing_map = {doc.file_path: doc for doc in existing_docs}
            to_create, to_delete_ids = [], []
            found_views = set(views)

            for v in views:
                if v not in existing_map:
                    to_create.append(
                        {
                            "connector_id": connector_id,
                            "file_path": v,
                            "file_name": v,
                            "file_size": 0,
                            "status": DocStatus.IDLE,
                            "file_metadata": {"type": "view", "source": "sql_discovery"},
                        }
                    )
            for path, doc in existing_map.items():
                if path not in found_views:
                    to_delete_ids.append(doc.id)

            if to_create:
                await self.document_repo.create_batch(to_create)
            if to_delete_ids:
                await self.document_repo.delete_batch(to_delete_ids)
            await self.db.commit()
            stats = {"added": len(to_create), "deleted": len(to_delete_ids), "updated": 0}

        total = await self.document_repo.count_by_connector(connector_id)
        updated_c = await self.connector_repo.update(connector_id, {"total_docs_count": total})
        resp = ConnectorResponse.model_validate(updated_c)
        await manager.emit_connector_updated(resp.model_dump(mode="json"))
        return stats


async def get_sql_discovery_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SQLDiscoveryService:
    return SQLDiscoveryService(db, settings_service)
