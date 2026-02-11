import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import pyodbc
from llama_index.core.llms import ChatMessage, MessageRole
from qdrant_client.http import models as qmodels
from vanna.base import VannaBase

from app.core.settings import settings
from app.factories.llm_factory import LLMFactory
from app.factories.embedding_factory import EmbeddingProviderFactory
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class VectraCustomVanna(VannaBase):
    """
    Custom Vanna implementation that delegates AI operations to Vectra's factories.
    This ensures we use the exact same LLM and Embedding configuration as the rest of the app.

    Since Vectra handles vector storage externally (via Qdrant/LlamaIndex ingestion pipeline),
    we stub out Vanna's internal vector storage methods.
    """

    def __init__(
        self,
        config=None,
        llm=None,
        embedding_service=None,
        vector_service=None,
        connector_id=None,
        collection_name=None,
    ):
        super().__init__(config=config)
        self.run_sql_is_set = True
        self.llm = llm
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.connector_id = str(connector_id) if connector_id else None
        self.collection_name = collection_name

    # --- Abstract Methods Implementation (Stubs/Retrieval) ---
    def add_ddl(self, ddl: str, **kwargs) -> str:
        return "storage-handled-externally"

    def add_documentation(self, documentation: str, **kwargs) -> str:
        return "storage-handled-externally"

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        return "storage-handled-externally"

    def get_related_ddl(self, question: str, **kwargs) -> list:
        """
        Retrieve related DDL from Qdrant using the embedding service.
        This provides the context Vanna needs to generate SQL.
        """
        if not self.vector_service or not self.connector_id:
            logger.warning("Vector Service or Connector ID not set in Vanna. Cannot retrieve DDL.")
            return []

        try:
            # 1. Embed the question
            # self.embedding_service is the Model (BaseEmbedding), not the service.
            query_vector = self.embedding_service.get_text_embedding(question)

            # 2. Get Sync Client
            client = self.vector_service.get_qdrant_client()

            # 3. Use Injected Collection Name
            if not self.collection_name:
                logger.warning("No collection name provided to Vanna. Falling back to default 'gemini_collection'.")
                self.collection_name = "gemini_collection"

            collection_name = self.collection_name

            # 4. Search Qdrant
            logger.info(f"Vanna DDLocal Search | Collection: {collection_name} | Connector: {self.connector_id}")

            # Use query_points instead of search (version compatibility)
            result = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=10,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="connector_id", match=qmodels.MatchValue(value=self.connector_id)),
                        qmodels.FieldCondition(key="type", match=qmodels.MatchValue(value="sql_view_schema")),
                    ]
                ),
            )

            # query_points returns QueryResponse with 'points' attribute in some versions, or list
            points = result.points if hasattr(result, "points") else result

            logger.info(f"Vanna Qdrant Hits: {len(points)}")

            # 5. Extract DDL
            ddl_list = []

            for hit in points:
                payload = hit.payload or {}

                # 1. Try standard 'content' or 'text' keys
                content = payload.get("content") or payload.get("text")

                # 2. LlamaIndex Fallback: Parse _node_content JSON
                if not content and "_node_content" in payload:
                    try:
                        node_content = json.loads(payload["_node_content"])
                        content = node_content.get("text")
                    except Exception as e:
                        logger.warning(f"Failed to parse _node_content for hit {hit.id}: {e}")

                if content:
                    # P0 CLEANUP: Remove SQL noise (e.g. COLLATE) to help LLM focus on columns
                    # Matches COLLATE "..." up to the closing quote or next syntax
                    content_clean = re.sub(r'COLLATE\s+"[^"]+"', "", content, flags=re.IGNORECASE)
                    ddl_list.append(content_clean)

            logger.info(f"Vanna Retrieved {len(ddl_list)} DDL snippets for context.")
            return ddl_list

        except Exception as e:
            logger.error(f"Error retrieving DDL for Vanna: {e}")
            return []

    # ... (Rest of existing methods) ...
    def get_related_documentation(self, question: str, **kwargs) -> list:
        return []

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        return []

    def get_training_data(self, **kwargs) -> pd.DataFrame:
        return pd.DataFrame()

    def remove_training_data(self, id: str, **kwargs) -> bool:
        return True

    def submit_prompt(self, prompt, **kwargs) -> str:
        if not self.llm:
            raise ValueError("LLM not initialized in Vanna Service")

        try:
            # Generate System Instruction (Dynamic)
            system_instruction = self._get_system_instructions()

            # P0 FIX: Detect if prompt is a List (Chat History) or String
            if isinstance(prompt, list):
                logger.info("Vanna submit_prompt: Detected Chat History (List). Using chat API.")
                messages = []

                # 1. Inject System Message FIRST
                messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_instruction))

                # 2. Add existing messages
                for msg in prompt:
                    role = MessageRole.USER
                    if msg.get("role") == "system":
                        # If upstream already provided a system message, we might overwrite or append.
                        # For now, let's allow multiple system messages or just skip if ours is better.
                        # Actually, LlamaIndex handles list of messages fine.
                        role = MessageRole.SYSTEM
                    elif msg.get("role") == "assistant":
                        role = MessageRole.ASSISTANT

                    messages.append(ChatMessage(role=role, content=msg.get("content", "")))

                # Use sync API because VannaBase methods (like submit_prompt) are called synchronously.
                # Avoid asyncio.run() inside a thread that may already have an event loop (FastAPI).
                logger.info(f"Sending {len(messages)} messages to LLM via chat...")
                response = self.llm.chat(messages)
                response_text = response.message.content if hasattr(response, "message") else str(response)

            else:
                # String prompts (standard completion)
                logger.info(
                    "Vanna submit_prompt: Detected String. Wrapping in Chat Structure for System Prompt support."
                )
                # We upgrade to Chat API to enforce System Prompt even for single strings
                messages = [
                    ChatMessage(role=MessageRole.SYSTEM, content=system_instruction),
                    ChatMessage(role=MessageRole.USER, content=str(prompt)),
                ]
                response = self.llm.chat(messages)
                response_text = response.message.content if hasattr(response, "message") else str(response)

            logger.info(f"Vanna LLM Response: {response_text}")
            return response_text

        except Exception as e:
            # P0: Catch broad exceptions for the fallback since we are blocking.
            logger.warning(f"LLM call failed, attempting fallback: {e}")
            if isinstance(prompt, list):
                # Re-construct messages for sync chat (already done but safe to retry completion if chat fails)
                try:
                    # In some rare cases where .chat fails, .complete might work or vice versa
                    response = self.llm.complete(str(prompt[-1].get("content", "")) if prompt else "")
                    return str(response)
                except Exception:
                    raise e
            else:
                response = self.llm.complete(str(prompt))
                return str(response)

    def generate_embedding(self, data: str) -> List[float]:
        if not self.embedding_service:
            raise ValueError("Embedding Service not initialized in Vanna Service")
        return self.embedding_service.get_text_embedding(data)

    def run_sql(self, sql: str, **kwargs) -> pd.DataFrame:
        params = getattr(self, "conn_params", {})
        params.update(kwargs)
        host = params.get("host") or settings.DB_HOST
        user = params.get("user") or settings.DB_USER
        password = params.get("password") or settings.DB_PASSWORD
        database = params.get("database") or settings.DB_NAME
        driver = params.get("driver", "{ODBC Driver 17 for SQL Server}")
        conn_str = f"DRIVER={driver};SERVER={host};DATABASE={database};UID={user};PWD={password}"
        try:
            # Mask password for logging
            logger.info(f"Vanna executing SQL on {host} (DB: {database})...")

            conn = pyodbc.connect(conn_str)
            try:
                df = pd.read_sql(sql, conn)
                return df
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Vanna SQL Execution failed: {e}")
            raise e

    def _get_dialect_instructions(self, db_type: str) -> str:
        """
        Returns specific SQL Prompt Rules based on the database type.
        This makes the connector agnostic and "smart".
        """
        db_type = db_type.lower()

        if db_type in ["mssql", "sqlserver", "sql-server", "odbc"]:
            return (
                "RULES FOR SQL SERVER (T-SQL):"
                "\n1. Do NOT use LIMIT. Always use 'SELECT TOP n' at the start of the query."
                "\n2. Use T-SQL date functions (e.g. GETDATE(), DATEPART)."
                "\n3. Use brackets [ ] for column names with spaces or reserved keywords."
                "\n4. String concatenation uses '+' (not ||)."
            )

        elif db_type in ["postgres", "postgresql"]:
            return (
                "RULES FOR POSTGRESQL:"
                "\n1. Use 'LIMIT n' at the end of the query."
                '\n2. Use double quotes " for column names if case-sensitive.'
                "\n3. Use ANSI standard SQL functions."
            )

        elif db_type in ["mysql", "mariadb"]:
            return (
                "RULES FOR MYSQL:"
                "\n1. Use 'LIMIT n' at the end of the query."
                "\n2. Use backticks ` for column names."
            )

        elif db_type == "sqlite":
            return "RULES FOR SQLITE:" "\n1. Use 'LIMIT n'." "\n2. Use STRFTIME for dates."

        return "RULES: Follow standard ANSI SQL syntax."

    def _get_system_instructions(self) -> str:
        """
        Generates the System Prompt for the LLM.
        This provides the AI with "Personality" and technical context.
        """
        # 1. Database Context from Config (Dynamic Dialect Injection)
        db_type = self.config.get("type", "").lower()
        dialect_instruction = f"You are an expert SQL Data Analyst.\n{self._get_dialect_instructions(db_type)}"

        # 2. Visualization Context (Multilingual Support)
        viz_instruction = (
            "When asked for visualizations, interpret terms in any language:\n"
            "- 'circulaire', 'camembert', 'secteurs' -> Pie Chart\n"
            "- 'barres', 'batons' -> Bar Chart\n"
            "- 'courbe', 'evolution' -> Line Chart\n"
            "Always choose the best visualization for the data if not specified."
        )

        # 3. Critical Safety Instruction (P0 FIX)
        # Ensure the LLM never returns plain text that could crash the DB driver
        safety_instruction = (
            "\nCRITICAL: If you cannot answer the question (e.g. insufficient context, missing columns), "
            "you MUST return a valid SQL comment explaining why.\n"
            "Example: -- ERROR: I cannot answer because the 'customers' table is missing.\n"
            "DO NOT return plain text. ONLY return valid SQL or Comments."
        )

        # 4. Anti-Hallucination
        # The LLM must NOT guess table names.
        hallucination_instruction = (
            "\nIMPORTANT: You are restricted to the Database Schema provided in the context."
            "\n- DO NOT assume the existence of tables unless they are explicitly defined in the context."
            "\n- If you are unsure which column to use, return a SQL comment asking for clarification."
        )

        return f"{dialect_instruction}\n\n{viz_instruction}\n{safety_instruction}\n{hallucination_instruction}"

    def submit_question(self, question: str, **kwargs) -> dict:
        try:
            self.conn_params = kwargs
            ask_kwargs = {
                k: v for k, v in kwargs.items() if k not in ["host", "port", "user", "password", "database", "driver"]
            }

            logger.info(f"VANNA_QUERY | Asking: {question}")

            # --- manually implement RAG Loop to ensure Context + Validation ---

            # 1. Retrieve Context (DDL)
            ddl_list = self.get_related_ddl(question)

            # 2. Construct Prompt with Context
            ddl_context = "\n\n".join(ddl_list)

            if not ddl_context:
                logger.warning("VANNA_QUERY | No DDL context found! automatic hallucination risk.")

            full_prompt = f"The user asked: {question}\n\nUse this DDL to generate the SQL:\n{ddl_context}"

            # 3. Get LLM Response
            # submit_prompt injects the System Message (Personality + Safety)
            llm_response = self.submit_prompt(full_prompt, **ask_kwargs)

            if not llm_response:
                return {"error": "Empty response from LLM"}

            # 4. Simple Safety Guard
            cleaned_response = llm_response.strip()

            if cleaned_response.startswith("```"):
                lines = cleaned_response.split("\n")
                if len(lines) >= 3:
                    cleaned_response = "\n".join(lines[1:-1]).strip()

            cleaned_response = re.sub(r"/\*[\s\S]*?\*/", "", cleaned_response).strip()

            valid_prefixes = ("SELECT", "WITH", "SHOW", "DESCRIBE", "--", "/*")

            if not cleaned_response.upper().startswith(valid_prefixes):
                logger.warning(f"VANNA_QUERY | Response validation failed (Not SQL): {cleaned_response[:50]}...")
                return {"sql": None, "dataframe": None, "figure": None, "text": llm_response}

            # 5. Execute
            sql = cleaned_response
            logger.info(f"VANNA_QUERY | Executing SQL: {sql}")

            if sql.startswith("-- ERROR:"):
                return {"sql": sql, "dataframe": None, "figure": None, "text": sql.replace("-- ERROR:", "").strip()}

            df = self.run_sql(sql, **self.conn_params)
            fig = None

            return {"sql": sql, "dataframe": df, "figure": fig}

        except Exception as e:
            logger.error(f"Vanna submit_question failed: {e}")
            return {"error": str(e)}

    # Necessary overrides for VannaBase but we can keep simple
    def system_message(self, message: str) -> Any:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> Any:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> Any:
        return {"role": "assistant", "content": message}


async def VannaServiceFactory(
    settings_service: SettingsService,
    connector_id: str = None,
    context_provider: str = None,
    connector_config: dict = None,
):
    """
    Async Factory to return the configured Vanna Service.
    Uses centralized factories for LLM and Embeddings.
    Arguments:
        context_provider: Specific AI provider for this connector (optional).
                          If provided, used for Embedding Model AND Collection resolution.
        connector_config: Configuration dictionary for the connector (DB type, host, etc.)
    """
    # 1. Determine Provider for Vectors (Connector Specific)
    vector_provider = context_provider if context_provider else settings.EMBEDDING_PROVIDER

    logger.info(f"Vanna Factory | Vector Provider: {vector_provider} | LLM Provider: {settings.EMBEDDING_PROVIDER}")

    # 2. Create Embedding Engine (Async) - Used for Query Embedding (Must match Vector Store)
    embedding_model = await EmbeddingProviderFactory.create_embedding_model(
        provider=vector_provider, settings_service=settings_service
    )

    # 3. Create LLM Engine using centralized Factory
    # We use the GLOBAL provider for LLM (Intelligence), independent of where vectors are stored.
    # This allows Hybrid Mode: Local Vectors + Cloud LLM (e.g. OpenAI)
    from app.factories.chat_engine_factory import ChatEngineFactory

    llm = await ChatEngineFactory.create_from_provider(
        provider=settings.EMBEDDING_PROVIDER, settings_service=settings_service
    )

    # 4. Instantiate VectorService (for context retrieval)
    from app.services.vector_service import VectorService

    vector_service = VectorService(settings_service)

    # 5. Resolve Collection Name (Must match Vector Provider)
    collection_name = await vector_service.get_collection_name(provider=vector_provider)

    # 6. Return Custom Vanna Instance with Collection Context
    # 6. Return Custom Vanna Instance with Collection Context
    return VectraCustomVanna(
        config=connector_config or {},
        llm=llm,
        embedding_service=embedding_model,
        vector_service=vector_service,
        connector_id=connector_id,
        collection_name=collection_name,
    )


# Alias for import compatibility
VectraVannaService = VannaServiceFactory
