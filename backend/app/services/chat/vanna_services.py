import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import nest_asyncio

# Patch asyncio to allow nested event loops (fixing RuntimeError in async environments like FastAPI + Pandas/SQLAlchemy)
nest_asyncio.apply()

try:
    import pyodbc
except ImportError:
    pyodbc = None
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
        """
        Store a successful Question-SQL pair in Qdrant for few-shot learning.
        """
        if not self.vector_service or not self.connector_id:
            logger.warning("Vanna | Vector Service or Connector ID not set. Cannot store training pair.")
            return "skipped"

        try:
            # 1. Generate unique ID for the point
            import uuid

            point_id = str(uuid.uuid4())

            # 2. Embed the question
            vector = self.embedding_service.get_text_embedding(question)

            # 3. Prepare payload
            payload = {
                "connector_id": self.connector_id,
                "type": "sql_training_pair",
                "question": question,
                "sql": sql,
                "text": f"Question: {question}\nSQL: {sql}",  # For keyword search fallback if needed
                "metadata": kwargs.get("metadata", {}),
            }

            # 4. Upsert to Qdrant (Sync)
            client = self.vector_service.client
            client.upsert(
                collection_name=self.collection_name,
                points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
            )
            logger.info(f"Vanna | Stored training pair: {question}")
            return point_id

        except Exception as e:
            logger.error(f"Vanna | Failed to store training pair: {e}")
            return "error"

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

            # 2. Get Sync Client (Pre-initialized in Factory)
            client = self.vector_service.client
            if not client:
                logger.error("Vanna | Qdrant client not initialized. Cannot retrieve DDL.")
                return []

            # 3. Use Injected Collection Name
            if not self.collection_name:
                logger.warning("No collection name provided to Vanna. Falling back to default 'gemini_collection'.")
                self.collection_name = "gemini_collection"

            collection_name = self.collection_name

            # 4. Search Qdrant
            logger.info(f"Vanna DDL Search | Collection: {collection_name} | Connector: {self.connector_id}")

            # Use query_points instead of search (version compatibility)
            result = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=15,  # Increased limit to improve context for complex queries
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
        """
        Retrieve similar Question-SQL pairs from Qdrant for few-shot learning.
        """
        if not self.vector_service or not self.connector_id:
            return []

        try:
            query_vector = self.embedding_service.get_text_embedding(question)
            client = self.vector_service.client
            collection_name = self.collection_name

            result = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=5,  # Top 5 similar examples
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="connector_id", match=qmodels.MatchValue(value=self.connector_id)),
                        qmodels.FieldCondition(key="type", match=qmodels.MatchValue(value="sql_training_pair")),
                    ]
                ),
            )

            points = result.points if hasattr(result, "points") else result
            examples = []
            for hit in points:
                payload = hit.payload or {}
                if "question" in payload and "sql" in payload:
                    examples.append({"question": payload["question"], "sql": payload["sql"]})

            logger.info(f"Vanna | Retrieved {len(examples)} training examples.")
            return examples

        except Exception as e:
            logger.error(f"Vanna | Error retrieving training pairs: {e}")
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
        driver = params.get("driver", "ODBC Driver 17 for SQL Server")

        # Helper to construct SQLAlchemy URL
        # We use mssql+pyodbc for SQL Server
        if "ODBC" in driver or "SQL Server" in driver:
            # Strip curly braces if present (e.g. {ODBC Driver 17 for SQL Server})
            driver_clean = driver.replace("{", "").replace("}", "")
            driver_encoded = driver_clean.replace(" ", "+")
            connection_url = (
                f"mssql+pyodbc://{user}:{password}@{host}/{database}?driver={driver_encoded}&TrustServerCertificate=yes"
            )
        else:
            # Fallback for others (Postgres/MySQL not fully implemented here yet, but structure allows it)
            connection_url = f"mssql+pyodbc://{user}:{password}@{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"

        try:
            # Mask password for logging
            logger.info(f"Vanna executing SQL on {host} (DB: {database})...")

            # Create Engine (disposable for this call to avoid global state issues in this context,
            # though caching would be better in production)
            from sqlalchemy import create_engine

            engine = create_engine(connection_url)

            with engine.connect() as conn:
                df = pd.read_sql(sql, conn)
                return df

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
                "\n2. DATE CALCULATIONS: Use simple comparisons."
                "\n   - Last 3 years: YearColumn >= YEAR(GETDATE()) - 3"
                "\n   - Recent dates: DateColumn >= DATEADD(day, -30, GETDATE())"
                "\n   - DO NOT use complex math like DATEADD(year, -DATEPART(yyyy, GETDATE()), ...) as it causes overflows."
                "\n3. CRITICAL: Do NOT use aliases in WHERE, GROUP BY, HAVING or ORDER BY clauses. You MUST repeat the full expression."
                "\n   - WRONG: SELECT DATEPART(yy, Date) as Year ... WHERE Year = 2024 GROUP BY Year"
                "\n   - RIGHT: SELECT DATEPART(yy, Date) as Year ... WHERE DATEPART(yy, Date) = 2024 GROUP BY DATEPART(yy, Date)"
                "\n4. Avoid quoting column names unless they contain special characters."
                "\n5. Use 'TOP 1000' if no specific limit is requested to prevent massive results."
                "\n6. PREFER existing columns: If 'AnneeVente' exists, use it instead of DATEPART(year, DateVente)."
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
        target_schema = self.config.get("schema")

        dialect_instruction = f"You are an expert SQL Data Analyst.\n{self._get_dialect_instructions(db_type)}"

        if target_schema:
            dialect_instruction += f"\nIMPORTANT: The database schema is '{target_schema}'. You MUST prefix ALL table names with '{target_schema}.' (e.g. FROM {target_schema}.TableName)."

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
            "\n- ALWAYS use the full table name exactly as shown in the DDL, including the schema (e.g. 'schema.table')."
            "\n- If you are unsure which column to use, return a SQL comment asking for clarification."
        )

        # 5. Output Format (JSON)
        # We enforce JSON to robustly handle conversational LLMs (Ollama, etc.)
        format_instruction = (
            "\nOUTPUT FORMAT:"
            "\nYou MUST return a single JSON object. Do not wrap it in markdown block."
            "\nIMPORTANT: The 'sql' string must be a single line or properly escaped with \\n. Do NOT use actual newlines."
            "\n{"
            '\n  "sql": "SELECT ...", '
            '\n  "explanation": "Brief explanation of the query..."'
            "\n}"
            "\nIf you cannot answer, return validation error in the 'explanation' field and null for 'sql'."
            "\n\nSELF-CORRECTION CHECK:"
            "\nBefore completing the JSON, verify that:"
            "\n1. No aliases are used in WHERE, GROUP BY, or HAVING clauses."
            "\n2. Full expressions are repeated instead of aliases in these clauses."
            "\n3. Existing columns (like 'AnneeVente') are used instead of calculating them if they satisfy the query."
        )

        system_prompt = f"{dialect_instruction}\n\n{viz_instruction}\n{safety_instruction}\n{hallucination_instruction}\n{format_instruction}"
        logger.info(
            f"VANNA_SYSTEM_PROMPT | Schema Config: {self.config.get('schema')} | Prompt Preview: {system_prompt[:200]}..."
        )
        return system_prompt

    def _extract_json_from_response(self, text: str) -> dict:
        """
        Robustly extracts JSON from LLM response.
        Handles Markdown wrapping (```json ... ```) or raw JSON in text.
        """
        try:
            # 1. Try direct parse
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Extract from Markdown code block
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Extract from first '{' to last '}'
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start : end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        return {}

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

            # 2. Retrieve Similar Examples (Few-Shot)
            examples = self.get_similar_question_sql(question)
            example_context = ""
            if examples:
                example_context = "\n\nUSE THESE EXAMPLES AS REFERENCE:\n"
                for exp in examples:
                    example_context += f"Question: {exp['question']}\nSQL: {exp['sql']}\n\n"

            # 3. Construct Prompt with Context
            ddl_context = "\n\n".join(ddl_list)

            target_schema = self.config.get("schema")
            db_type = self.config.get("type", "").lower()

            # Additional Dialect Reinforcement
            reinforcement = ""
            if db_type in ["mssql", "sqlserver", "sql-server", "odbc"]:
                reinforcement = (
                    "\nFINAL REMINDER FOR SQL SERVER (T-SQL):"
                    "\n- NO ALIASES in WHERE, GROUP BY, HAVING, or ORDER BY."
                    "\n- USE EXISTING COLUMNS: If 'AnneeVente' or 'Annee' is in the DDL, use it instead of calculations."
                    "\n- SIMPLE DATE MATH: For 'last 3 years', use 'AnneeVente >= YEAR(GETDATE()) - 3' or 'YEAR(DateColumn) >= YEAR(GETDATE()) - 3'."
                    "\n- CRITICAL: Never subtract current year from GETDATE() (e.g. DATEADD(year, -2026, ...)) as it causes YEAR 0 errors."
                )

            if target_schema:
                # REINFORCEMENT: Add explicit schema rule right before the DDL
                ddl_context = f"IMPORTANT RULE: All tables below are in the '{target_schema}' schema. You MUST use '{target_schema}.TableName' in your SQL.\n\n{ddl_context}"

            if not ddl_context:
                logger.warning("VANNA_QUERY | No DDL context found! automatic hallucination risk.")

            full_prompt = (
                f"The user asked: {question}\n\n"
                f"Use this DDL to generate the SQL:\n{ddl_context}"
                f"{example_context}"
                f"{reinforcement}"
            )

            # 4. Get LLM Response
            # submit_prompt injects the System Message (Personality + Safety)
            llm_response = self.submit_prompt(full_prompt, **ask_kwargs)

            if not llm_response:
                return {"error": "Empty response from LLM"}

            # 4. JSON Extraction & Validation
            parsed_response = self._extract_json_from_response(llm_response)

            sql = parsed_response.get("sql")
            explanation = parsed_response.get("explanation")

            if not sql:
                # Fallback: simple text response (likely an error or refinement question)
                logger.warning(f"VANNA_QUERY | No SQL found in JSON. Response: {llm_response}")
                return {"sql": None, "dataframe": None, "figure": None, "text": explanation or llm_response}

            # Final Cleanup of the extracted SQL
            sql = re.sub(r"/\*[\s\S]*?\*/", "", sql).strip()

            # 5. Execute with Retry Loop
            max_retries = 2
            current_try = 0
            last_error = None

            while current_try < max_retries:
                current_try += 1
                logger.info(f"VANNA_QUERY | Executing SQL (Try {current_try}): {sql}")

                # Check if it's just a comment (LLM following "return comment on error" instruction)
                if sql.startswith("--") or sql.startswith("/*"):
                    logger.warning(f"VANNA_QUERY | SQL is a comment (execution skipped): {sql}")
                    return {"sql": None, "dataframe": None, "figure": None, "text": sql.replace("--", "").strip()}

                if sql.startswith("-- ERROR:"):
                    return {"sql": sql, "dataframe": None, "figure": None, "text": sql.replace("-- ERROR:", "").strip()}

                try:
                    df = self.run_sql(sql, **self.conn_params)

                    # --- Auto-Learning Loop ---
                    if df is not None and not df.empty:
                        auto_learn = self.config.get("auto_learn", True)
                        if auto_learn:
                            logger.info(f"Vanna | Auto-Learning: Storing successful Question-SQL pair.")
                            self.add_question_sql(question=question, sql=sql)

                    return {"sql": sql, "dataframe": df, "figure": None, "text": explanation}

                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"VANNA_QUERY | Execution failed (Try {current_try}/{max_retries}): {last_error}")

                    if current_try >= max_retries:
                        break

                    # --- Self-Correction Logic ---
                    # Provide the error back to the LLM and ask for a fix
                    correction_prompt = (
                        f"The generated SQL failed with this error: {last_error}\n\n"
                        f"Original Question: {question}\n"
                        f"Invalid SQL: {sql}\n\n"
                        "Please fix the SQL. "
                    )

                    if "Invalid column name" in last_error and db_type in ["mssql", "sqlserver", "sql-server"]:
                        correction_prompt += (
                            "CRITICAL: SQL Server does NOT allow aliases in WHERE, GROUP BY, or HAVING. "
                            "You must repeat the full expression or use an existing column from the DDL. "
                        )

                    if "overflow" in last_error or "22007" in last_error:
                        correction_prompt += (
                            "CRITICAL: Your date calculation caused an OVERFLOW. "
                            "Use simpler logic like 'YearColumn >= YEAR(GETDATE()) - 3'. "
                            "Avoid subtracting huge values like the current year from GETDATE(). "
                        )

                    llm_response = self.submit_prompt(correction_prompt, **ask_kwargs)
                    parsed_response = self._extract_json_from_response(llm_response)
                    sql = parsed_response.get("sql")
                    explanation = parsed_response.get("explanation")

                    if not sql:
                        break
                    sql = re.sub(r"/\*[\s\S]*?\*/", "", sql).strip()

            # If we reached here, it means all retries failed
            return {
                "sql": None,
                "dataframe": None,
                "figure": None,
                "text": f"SQL Execution Error after {max_retries} attempts: {last_error}",
            }

        except Exception as e:
            logger.error(f"Vanna submit_question failed: {e}")
            # Return the error as text so the frontend displays it
            return {"sql": None, "dataframe": None, "figure": None, "text": f"SQL Execution Error: {str(e)}"}

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
    # Priority:
    # A. Connector Specific Provider (from UI/DB)
    # B. Global Default from DB/SettingsService
    # C. Env Fallback (handled by settings_service)

    global_embedding_provider = await settings_service.get_value("embedding_provider")
    vector_provider = context_provider if context_provider else global_embedding_provider

    logger.info(
        f"Vanna Factory | Vector Provider: {vector_provider} | LLM Provider (Global): {global_embedding_provider}"
    )

    # 2. Create Embedding Engine (Async) - Used for Query Embedding (Must match Vector Store)
    embedding_model = await EmbeddingProviderFactory.create_embedding_model(
        provider=vector_provider, settings_service=settings_service
    )

    # 3. Create LLM Engine using centralized Factory
    # We use the GLOBAL provider for LLM (Intelligence), independent of where vectors are stored.
    # This allows Hybrid Mode: Local Vectors + Cloud LLM (e.g. OpenAI)
    from app.factories.chat_engine_factory import ChatEngineFactory

    llm = await ChatEngineFactory.create_from_provider(
        provider=global_embedding_provider, settings_service=settings_service
    )

    # 4. Instantiate VectorService (for context retrieval)
    from app.services.vector_service import VectorService

    vector_service = VectorService(settings_service)

    # 5. Resolve Collection Name (Must match Vector Provider)
    collection_name = await vector_service.get_collection_name(provider=vector_provider)

    # 5.1 Pre-initialize Qdrant Client (Sync) for Vanna's sync methods
    await vector_service.get_qdrant_client()

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
