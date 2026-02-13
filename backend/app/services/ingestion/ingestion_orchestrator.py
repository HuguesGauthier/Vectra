import asyncio
import hashlib
import json
import logging
import multiprocessing
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Union
from uuid import UUID

from fastapi import Depends

# LlamaIndex Imports
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client.http import models as qmodels
from qdrant_client.http.models import PointStruct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager, Websocket
from app.core.exceptions import TechnicalError
from app.core.settings import settings
from app.factories.ingestion_factory import IngestionFactory
from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.enums import ConnectorStatus, DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.services.ingestion.processors.csv_processor import CsvStreamProcessor
from app.services.settings_service import SettingsService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)
logger.debug("ingestion_orchestrator.py loaded")


class IngestionStoppedError(Exception):
    pass


class ConnectorStatusCache:
    """Helper to catch connector status and avoid N+1 DB queries."""

    def __init__(self, repo: ConnectorRepository, connector_id: UUID, ttl_seconds: int = 5):
        self._repo = repo
        self._cid = connector_id
        self._ttl = ttl_seconds
        self._last_check = 0
        self._status = ConnectorStatus.IDLE

    async def get_status(self) -> ConnectorStatus:
        now = time.time()
        if now - self._last_check > self._ttl:
            connector = await self._repo.get_by_id(self._cid)
            self._status = connector.status if connector else ConnectorStatus.ERROR
            self._last_check = now
        return self._status


from app.services.sql_discovery_service import SQLDiscoveryService


class IngestionOrchestrator:
    """
    Coordinator for the ingestion process.
    Responsible for binding the DB, FileSystem, and Vector DB together in a non-blocking, safe way.

    Refactored for Dependency Injection, Safety, and Performance (P0-P2 Audit).
    """

    def __init__(
        self,
        db: AsyncSession,
        vector_repo: VectorRepository,
        # P1: Dependency Injection
        settings_service: Annotated[SettingsService, Depends(SettingsService)],
        vector_service: Annotated[VectorService, Depends(VectorService)],
        sql_discovery_service: Optional[SQLDiscoveryService] = None,
        # Use simple DI for repos if needed, otherwise instantiate with db is fine for repos
    ):
        self.db = db
        self.vector_repo = vector_repo
        self.settings_service = settings_service
        self.vector_service = vector_service
        self.sql_discovery_service = sql_discovery_service

        self._processor_factory = CsvStreamProcessor

        # Repositories associated with this session
        self.connector_repo = ConnectorRepository(db)
        self.doc_repo = DocumentRepository(db)

    # --- PUBLIC DISPATCHER METHODS ---

    async def ingest_document(self, doc_id: UUID) -> None:
        """
        Smart dispatch to ingest a single document based on its type.
        """
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Route based on file type
        logger.info(f"🔀 Routing document {doc_id} | Path: '{doc.file_path}'")

        if doc.file_path.lower().strip().endswith(".csv"):
            logger.info("👉 Routing to Smart CSV Pipeline")
            await self.ingest_csv_document(doc_id)
        else:
            logger.info("👉 Routing to Generic LlamaIndex Pipeline")
            # Standard generic file
            connector = await self.connector_repo.get_by_id(doc.connector_id)
            if not connector:
                raise ValueError("Connector not found")

            # Setup Pipeline once
            pipeline, vector_store, batch_size, workers, text_splitter, docstore = await self.setup_pipeline(connector)

            # Reconstruct path
            from app.core.interfaces.base_connector import get_full_path_from_connector

            full_path = get_full_path_from_connector(connector, doc.file_path)

            await self.ingest_files(
                file_paths=[(full_path, doc.file_path)],
                pipeline=pipeline,
                vector_store=vector_store,
                connector_id=connector.id,
                connector_acl=connector.configuration.get("connector_acl", []),
                batch_size=batch_size,
                num_workers=workers,
                docs_map={doc.file_path: doc},
                force_reingest=True,
                text_splitter=text_splitter,
                docstore=docstore,
                ignore_connector_status=True,
                overall_total_files=1,
            )

    async def ingest_batch(self, connector_id: UUID, docs: List[ConnectorDocument]) -> None:
        """
        Ingest a mixed batch of documents. Routes CSVs separately from generic files.
        """
        connector = await self.connector_repo.get_by_id(connector_id)
        if not connector:
            raise ValueError(f"Connector {connector_id} not found")

        # Routing by connector type: SQL (including Vanna SQL)
        if connector.connector_type in ["sql", "vanna_sql"]:
            logger.info(f"🗄️ SQL Batch Ingestion | Count: {len(docs)}")
            for d in docs:
                try:
                    await self.ingest_sql_view(d.id, connector)
                except Exception as e:
                    logger.error(f"SQL View Ingestion Error {d.id}: {e}")
            return

        csv_docs = [d for d in docs if d.file_path.strip().lower().endswith(".csv")]
        generic_docs = [d for d in docs if not d.file_path.strip().lower().endswith(".csv")]

        logger.info(f"📦 Batch Ingestion | Total: {len(docs)} | CSVs: {len(csv_docs)} | Generic: {len(generic_docs)}")
        if csv_docs:
            logger.info(f"📄 CSVs to process: {[d.file_path for d in csv_docs]}")

        # 1. Process CSVs (Serial is safer for heavy logic)
        for d in csv_docs:
            try:
                await self.ingest_csv_document(d.id)
            except Exception as e:
                logger.error(f"Batch CSV Error {d.id}: {e}")
                # Continue batch

        # 2. Process Generic Files (Parallel Pipeline)
        if generic_docs:
            connector = await self.connector_repo.get_by_id(connector_id)
            pipeline, vector_store, batch_size, workers, text_splitter, docstore = await self.setup_pipeline(connector)

            from app.core.interfaces.base_connector import get_full_path_from_connector

            file_paths = []
            docs_map = {}
            for d in generic_docs:
                full_path = get_full_path_from_connector(connector, d.file_path)
                file_paths.append((full_path, d.file_path))
                docs_map[d.file_path] = d

            await self.ingest_files(
                file_paths=file_paths,
                pipeline=pipeline,
                vector_store=vector_store,
                connector_id=connector_id,
                connector_acl=connector.configuration.get("connector_acl", []),
                batch_size=batch_size,
                num_workers=workers,
                docs_map=docs_map,
                force_reingest=True,
                text_splitter=text_splitter,
                docstore=docstore,
                ignore_connector_status=True,
                overall_total_files=len(generic_docs),
            )

    # --- GENERIC FILE INGESTION (LlamaIndex Pipeline) ---

    async def setup_pipeline(self, connector: Connector):
        """
        Setup the LlamaIndex IngestionPipeline for generic files.
        NOW WITH CACHING ENABLED for massive performance/cost savings!
        """
        try:
            client = self.vector_service.get_qdrant_client()
            aclient = self.vector_service.get_async_qdrant_client()
            provider = connector.configuration.get("ai_provider")
            collection = await self.vector_service.get_collection_name(provider)

            vector_store = QdrantVectorStore(client=client, aclient=aclient, collection_name=collection)

            workers = 5
            batch_size = 50 if provider != "local" else 5

            # Use threading for embeddings
            os.environ["OMP_NUM_THREADS"] = str(workers)

            embed_model = await self.vector_service.get_embedding_model(
                threads=workers, batch_size=batch_size, provider=provider
            )

            # Ensure Collection Exists
            if not client.collection_exists(collection):
                client.create_collection(
                    collection_name=collection,
                    vectors_config=qmodels.VectorParams(
                        size=len(embed_model.get_text_embedding("test")), distance=qmodels.Distance.COSINE
                    ),
                )

            text_splitter = SentenceSplitter(chunk_size=connector.chunk_size, chunk_overlap=connector.chunk_overlap)

            # Build transformations pipeline
            transformations = [text_splitter]

            # Check if smart metadata extraction is enabled
            indexing_config = connector.configuration.get("indexing_config", {})
            use_smart_extraction = indexing_config.get("use_smart_extraction", False)

            if use_smart_extraction:
                logger.info("✨ Smart metadata extraction ENABLED for this connector")

                # Import extractor
                from app.core.ingestion.extractors import ComboMetadataExtractor

                # Get fast LLM for extraction
                extraction_model = await self.settings_service.get_value("gemini_extraction_model")

                # Instantiate LLM for extraction
                from llama_index.llms.google_genai import GoogleGenAI

                api_key = await self.settings_service.get_value("gemini_api_key")

                if not extraction_model:
                    logger.warning("⚠️ gemini_extraction_model not configured. Skipping smart extraction.")
                elif not api_key:
                    logger.warning("⚠️ Gemini API key not found. Skipping smart extraction.")
                else:
                    extraction_llm = GoogleGenAI(
                        model=extraction_model, api_key=api_key, temperature=0.0  # Deterministic for extraction
                    )

                    # Retrieve application language preference (defaulting to 'fr' if not found)
                    app_language = await self.settings_service.get_value("app_language", "fr")

                    # Add extractor to pipeline (before embedding)
                    extractor = ComboMetadataExtractor(
                        llm=extraction_llm, extraction_model=extraction_model, language=app_language
                    )
                    transformations.append(extractor)

                    # Add formatter (after extraction, before embedding)
                    from app.core.ingestion.extractors import MetadataFormatter

                    formatter = MetadataFormatter()
                    transformations.append(formatter)

                    logger.info(f"🚀 Using {extraction_model} for metadata extraction")

            # Add embedding model (last step)
            transformations.append(embed_model)

            # ============================================================================
            # CACHE CONFIGURATION (P0: Cost/Performance Optimization)
            # ============================================================================
            from llama_index.core.ingestion import IngestionCache
            from llama_index.core.storage.docstore import SimpleDocumentStore
            from llama_index.core.storage.kvstore import SimpleKVStore

            # Create cache directory per connector (isolated caches)
            cache_dir = Path(".cache") / "ingestion" / str(connector.id)
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Initialize cache components
            # SimpleKVStore uses a single file
            kv_path = cache_dir / "kv_store.json"
            if kv_path.exists():
                kv_store = SimpleKVStore.from_persist_path(str(kv_path))
            else:
                kv_store = SimpleKVStore()

            # SimpleDocumentStore usually persists to a file as well in simple mode
            doc_path = cache_dir / "docstore.json"
            if doc_path.exists():
                docstore = SimpleDocumentStore.from_persist_path(str(doc_path))
                logger.info(f"💾 Loaded docstore from {doc_path} with {len(docstore.docs)} docs")
            else:
                docstore = SimpleDocumentStore()
                logger.info("🆕 Created new empty docstore")

            cache = IngestionCache(cache=kv_store, docstore=docstore, collection="pipeline_cache")

            logger.info(f"💾 Cache enabled at: {cache_dir}")

            # ============================================================================
            # PIPELINE CREATION (With Cache + Vector Store)
            # ============================================================================
            pipeline = IngestionPipeline(
                transformations=transformations,
                vector_store=vector_store,  # ← Automatic indexing!
                cache=cache,  # ← Enable caching!
                docstore=docstore,  # ← Document tracking
            )

            # ATTRIBUTE HACK FAILED: cannot attach to Pydantic model
            # We return docstore appropriately now.

            return pipeline, vector_store, batch_size, workers, text_splitter, docstore

        except Exception as e:
            # P0: Log exception but avoid dumping secrets if any
            logger.error(f"Setup Components Failed: {str(e)}", exc_info=True)
            raise TechnicalError(f"Setup Components Failed: {e}")

    async def ingest_files(
        self,
        file_paths: List[Union[str, tuple]],
        pipeline: IngestionPipeline,
        vector_store: QdrantVectorStore,
        connector_id: UUID,
        connector_acl: List[str],
        batch_size: int,
        num_workers: int,
        docs_map: Dict[str, ConnectorDocument],
        force_reingest: bool = False,
        text_splitter=None,
        docstore=None,  # Passed for explicit persistence
        ignore_connector_status: bool = False,
        overall_total_files: int = 0,
        initial_processed_count: int = 0,
    ):
        """
        Orchestrate the ingestion of a list of generic files (PDF, DOCX, etc).
        Optimized to batch everything into a single pipeline execution for performance.
        """
        start_time_total = time.time()
        status_cache = ConnectorStatusCache(self.connector_repo, connector_id)

        all_llama_documents = []
        valid_docs = []  # ConnectorDocument objects we actually found/processed parts of

        # 1. PREPARATION PHASE (Reading files)
        logger.info(f"🔄 Preparing {len(file_paths)} file(s) for batch ingestion...")

        for i, file_item in enumerate(file_paths):
            path, rel_path = file_item if isinstance(file_item, tuple) else (file_item, os.path.basename(file_item))
            doc = docs_map.get(rel_path)

            if not ignore_connector_status:
                current_status = await status_cache.get_status()
                if current_status == ConnectorStatus.PAUSED or current_status == ConnectorStatus.IDLE:
                    raise IngestionStoppedError("Stopped by user or system")

            if doc:
                await self.doc_repo.update(doc.id, {"status": DocStatus.PROCESSING})
                await manager.emit_document_update(str(doc.id), DocStatus.PROCESSING, "Reading...")

            try:
                # Load document using factory
                file_extension = Path(path).suffix
                processor = IngestionFactory.get_processor(file_extension)
                processed_docs = await processor.process(Path(path))

                from llama_index.core import Document as LlamaDocument

                file_llama_docs = []
                for idx, pd_doc in enumerate(processed_docs):
                    if not pd_doc.success:
                        logger.warning(f"Skipping failed part in {rel_path}: {pd_doc.error_message}")
                        continue

                    if not doc:
                        continue

                    # Build metadata
                    meta = pd_doc.metadata or {}
                    meta["connector_id"] = str(connector_id)
                    meta["connector_document_id"] = str(doc.id)
                    meta["file_name"] = doc.file_name
                    meta["connector_acl"] = connector_acl

                    # Create DETERMINISTIC ID for cache to work across re-runs
                    page_num = meta.get("page_number", idx)
                    chunk_idx = meta.get("chunk_index", 0)  # Support for non-paged content (Audio/Video)
                    stable_key = f"{path}:page:{page_num}:chunk:{chunk_idx}"
                    unique_id = hashlib.md5(stable_key.encode()).hexdigest()

                    llama_doc = LlamaDocument(
                        text=pd_doc.content,
                        id_=unique_id,
                        metadata=meta,
                        excluded_llm_metadata_keys=["connector_id", "connector_document_id"],
                        metadata_separator="\n",
                    )
                    file_llama_docs.append(llama_doc)

                if file_llama_docs:
                    all_llama_documents.extend(file_llama_docs)
                    if doc:
                        valid_docs.append(doc)
                else:
                    logger.warning(f"No content extracted from {rel_path}")
                    if doc:
                        await self.doc_repo.update(
                            doc.id, {"status": DocStatus.FAILED, "error_message": "No content extracted"}
                        )
                        await manager.emit_document_update(str(doc.id), DocStatus.FAILED, "No content extracted")

            except Exception as e:
                logger.error(f"File Preparation Fail for {rel_path}: {e}", exc_info=True)
                if doc:
                    await self.doc_repo.update(doc.id, {"status": DocStatus.FAILED, "error_message": str(e)})
                    await manager.emit_document_update(str(doc.id), DocStatus.FAILED, "Preparation Error")

            # Progress update for reading phase
            processed_count = initial_processed_count + i + 1
            percent = (processed_count / overall_total_files) * 100 if overall_total_files > 0 else 0
            await manager.emit_connector_progress(connector_id, processed_count, overall_total_files, percent)

        if not all_llama_documents:
            logger.info("ℹ️ No documents prepared for indexing.")
            return

        # 2. EXECUTION PHASE (Pipeline)
        try:
            # P0: Determine Optimized Worker Count
            if settings.ENABLE_PHOENIX_TRACING:
                workers = 0
                logger.debug("🕊️ Phoenix Tracing Enabled: Forcing synchronous execution (workers=0)")
            else:
                # Heuristic: Cap workers for API-based embedding (Gemini/OpenAI)
                # to avoid massive pickling overhead on Windows.
                is_local = False
                if pipeline.transformations:
                    # Check if any transformation is a local model (heuristic)
                    last_t_name = type(pipeline.transformations[-1]).__name__
                    if "HuggingFace" in last_t_name:
                        is_local = True

                cpu_count = multiprocessing.cpu_count()
                if not is_local:
                    # Remote APIs: Overhead of spawning 15 workers outweighs gain for small batches
                    workers = min(4, cpu_count)
                else:
                    workers = max(1, int(cpu_count * 0.75))

                logger.debug(f"⚡ Performance Mode: Using {workers} workers (is_local={is_local})")

            logger.info(
                f"🚀 Running batch ingestion pipeline for {len(all_llama_documents)} segments from {len(valid_docs)} file(s)..."
            )

            # Update all valid docs to 'Indexing'
            for doc in valid_docs:
                await manager.emit_document_update(str(doc.id), DocStatus.PROCESSING, "Embedding and indexing...")

            nodes = await pipeline.arun(documents=all_llama_documents, num_workers=workers, show_progress=False)

            # 3. FINALIZATION PHASE (Cleanup & Updates)
            nodes_by_doc: Dict[str, List] = {}
            if nodes:
                for node in nodes:
                    doc_id = node.metadata.get("connector_document_id")
                    if doc_id:
                        if doc_id not in nodes_by_doc:
                            nodes_by_doc[doc_id] = []
                        nodes_by_doc[doc_id].append(node)

            # P0 FIX: Helper for Self-Healing Stats
            async def _recover_vector_count(d_id):
                try:
                    provider = connector.configuration.get("ai_provider")
                    col = await self.vector_service.get_collection_name(provider)
                    return await self.vector_repo.count_by_document_id(col, d_id)
                except:
                    return 0

            now = datetime.now()
            for doc in valid_docs:
                doc_id_str = str(doc.id)
                doc_nodes = nodes_by_doc.get(doc_id_str, [])
                total_chunks = len(doc_nodes)

                if total_chunks == 0:
                    elapsed_ms = (time.time() - start_time_total) * 1000
                    await self.doc_repo.update(
                        doc.id,
                        {"status": DocStatus.INDEXED, "last_vectorized_at": now, "processing_duration_ms": elapsed_ms},
                    )
                    await manager.emit_document_update(
                        str(doc.id),
                        DocStatus.INDEXED,
                        "Already indexed (cache hit)",
                        last_vectorized_at=now,
                        processing_duration_ms=elapsed_ms,
                    )

                    # P0 FIX: Update DB with actual count (Self-Healing)
                    actual_count = await _recover_vector_count(doc.id)
                    if actual_count > 0:
                        await self.doc_repo.update(
                            doc.id, {"vector_point_count": actual_count, "chunks_total": actual_count}
                        )
                        logger.info(f"💾 CACHE HIT | Updated Doc {doc.id} with {actual_count} vectors")
                else:
                    token_count = sum(len(n.get_content()) for n in doc_nodes)
                    elapsed_ms = (time.time() - start_time_total) * 1000

                    await self.doc_repo.update(
                        doc.id,
                        {
                            "chunks_total": total_chunks,
                            "chunks_processed": total_chunks,
                            "vector_point_count": total_chunks,
                            "doc_token_count": token_count,
                            "status": DocStatus.INDEXED,
                            "last_vectorized_at": now,
                            "processing_duration_ms": elapsed_ms,
                        },
                    )

                    await manager.emit_document_update(
                        str(doc.id),
                        DocStatus.INDEXED,
                        f"Indexed {total_chunks} chunks",
                        doc_token_count=token_count,
                        vector_point_count=total_chunks,
                        last_vectorized_at=now,
                        processing_duration_ms=elapsed_ms,
                    )

            logger.info(f"✅ Batch pipeline complete: {len(nodes) if nodes else 0} total chunks indexed")

        except Exception as e:
            logger.error(f"❌ Batch pipeline execution failed: {e}", exc_info=True)
            for doc in valid_docs:
                await self.doc_repo.update(
                    doc.id, {"status": DocStatus.FAILED, "error_message": "Pipeline execution failed"}
                )
                await manager.emit_document_update(str(doc.id), DocStatus.FAILED, "Pipeline Error")
            raise

        # 4. PERSIST CACHE
        try:
            cache_dir = Path(".cache") / "ingestion" / str(connector_id)
            if hasattr(pipeline, "cache") and pipeline.cache:
                kv_path = cache_dir / "kv_store.json"
                if hasattr(pipeline.cache, "cache") and hasattr(pipeline.cache.cache, "persist"):
                    pipeline.cache.cache.persist(str(kv_path))

                doc_path = cache_dir / "docstore.json"
                docstore_ref = docstore or getattr(pipeline.cache, "docstore", None)
                if docstore_ref and hasattr(docstore_ref, "persist"):
                    docstore_ref.persist(str(doc_path))

                logger.info(f"💾 Ingestion cache persisted to {cache_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to persist ingestion cache: {e}")

    # --- CSV SPECIALIZED INGESTION ---

    async def ingest_csv_document(self, doc_id: UUID):
        """
        Orchestrates the ingestion of a single CSV document using SMART strategies.
        Guarantees state updates (FAILED/INDEXED) and prevents Event Loop blocking.
        """
        start_time = time.time()
        logger.info(f"Orchestrating SMART CSV ingestion for Doc {doc_id}")

        doc = None
        try:
            doc = await self.doc_repo.get_by_id(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            connector = await self.connector_repo.get_by_id(doc.connector_id)
            if not connector:
                raise ValueError("Connector not found")

            # 2. Setup
            await self.doc_repo.update(doc.id, {"status": DocStatus.PROCESSING})

            # Resolve Dependencies - Path Reconstruction
            from app.core.interfaces.base_connector import get_full_path_from_connector

            full_path = get_full_path_from_connector(connector, doc.file_path)

            # --- SMART PIPELINE FACTORY ---
            # Injected imports (better to be at top, but acceptable here for optional dependency isolation)
            from app.schemas.ingestion import IndexingStrategy
            from app.services.ingestion.transformers.smart_row_transformer import SmartRowTransformer

            file_metadata = doc.file_metadata or {}
            ai_schema_dict = file_metadata.get("ai_schema")

            # Initialize Strategy (Fallback to Defaults if missing)
            if ai_schema_dict:
                try:
                    strategy = IndexingStrategy(**ai_schema_dict)
                    logger.info(f"🧠 Using Smart Strategy: {strategy.model_dump_json(exclude_none=True)}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse Smart Strategy: {e}. Falling back to default.")
                    strategy = IndexingStrategy(renaming_map={})
            else:
                logger.info(f"No AI Schema for {doc_id}, using default mapping.")
                strategy = IndexingStrategy(renaming_map={})

            # Instantiate Transformer
            transformer = SmartRowTransformer(strategy)

            # Config
            provider = connector.configuration.get("ai_provider")
            collection_name = await self.vector_service.get_collection_name(provider=provider)
            embed_model = await self.vector_service.get_embedding_model(provider=provider)

            # P0 FIX: Ensure Collection Exists (was missing in CSV flow)
            client = self.vector_service.get_qdrant_client()
            if not client.collection_exists(collection_name):
                logger.info(f"Creating collection {collection_name}")
                from qdrant_client.http import models as qmodels

                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=len(embed_model.get_text_embedding("test")), distance=qmodels.Distance.COSINE
                    ),
                )

            # 2.5 CLEANUP (Fix Re-vectorization append bug)
            try:
                await self.vector_repo.delete_by_document_id(collection_name, doc.id)
            except Exception as e:
                logger.warning(f"Pre-ingestion cleanup failed for CSV doc {doc.id}: {e}")

            # 3. Stream & Process
            # 3. Stream & Process (Non-Blocking)
            # P0: Offload CPU-bound CSV parsing to thread pool to prevent Event Loop blocking
            processor = self._processor_factory()

            def _process_stream():
                """CPU-bound sync generator wrapper"""
                iterator = enumerate(processor.iter_records(file_path=full_path, renaming_map=strategy.renaming_map))
                return list(iterator)  # Consuming iterator in thread

            # Run parsing in thread
            records_with_lines = await asyncio.to_thread(_process_stream)
            logger.info(f"📊 CSV Parser found {len(records_with_lines)} records for Doc {doc.id}")

            total_processed = 0
            total_tokens = 0

            # Batch Buffers
            batch_texts = []
            batch_metadatas = []
            BATCH_SIZE = 50

            # Transformer is lightweight enough to run in loop,
            # or could be moved inside _process_stream if very heavy.
            # Given it's just dict manipulation, main loop is OK providing we await I/O.

            for line_idx, record in records_with_lines:
                # --- TRANSFORM ROW ---
                try:
                    semantic_text, payload = transformer.transform(record, line_idx)

                    batch_texts.append(semantic_text)
                    batch_metadatas.append(payload)

                    # --- PROCESS BATCH (Async I/O) ---
                    if len(batch_texts) >= BATCH_SIZE:
                        batch_tokens = await self._process_smart_batch(
                            batch_texts,
                            batch_metadatas,
                            doc,
                            connector,
                            embed_model,
                            collection_name,
                            connector_acl=connector.configuration.get("connector_acl", []),
                        )
                        total_processed += len(batch_texts)
                        total_tokens += batch_tokens
                        batch_texts = []
                        batch_metadatas = []
                except Exception as e:
                    logger.warning(f"Skipping malformed row {line_idx}: {e}")
                    continue

            # Final Batch
            if batch_texts:
                batch_tokens = await self._process_smart_batch(
                    batch_texts,
                    batch_metadatas,
                    doc,
                    connector,
                    embed_model,
                    collection_name,
                    connector_acl=connector.configuration.get("connector_acl", []),
                )
                total_processed += len(batch_texts)
                total_tokens += batch_tokens

            # 4. Success State
            elapsed_ms = (time.time() - start_time) * 1000
            now = datetime.now()
            await self.doc_repo.update(
                doc.id,
                {
                    "status": DocStatus.INDEXED,
                    "chunks_processed": total_processed,
                    "chunks_total": total_processed,
                    "vector_point_count": total_processed,
                    "doc_token_count": total_tokens,
                    "last_vectorized_at": now,
                    "processing_duration_ms": elapsed_ms,
                },
            )
            # Emit stats for frontend update
            await manager.emit_document_update(
                str(doc.id),
                DocStatus.INDEXED,
                f"Indexed {total_processed} smart records",
                vector_point_count=total_processed,
                doc_token_count=total_tokens,
                last_vectorized_at=now,
                processing_duration_ms=elapsed_ms,
            )

            elapsed = round(time.time() - start_time, 2)
            logger.info(f"Ingestion SUCCESS | Doc {doc_id} | {total_processed} records | {elapsed}s")

        except Exception as e:
            logger.error(f"Ingestion FAILED | Doc {doc_id} | Error: {e}", exc_info=True)
            if doc:
                try:
                    await self.doc_repo.update(doc.id, {"status": DocStatus.FAILED, "error_message": str(e)})
                except:
                    pass
            if doc:
                try:
                    await self.doc_repo.update(doc.id, {"status": DocStatus.FAILED, "error_message": str(e)})
                except:
                    pass
            raise e

    # --- SQL SPECIALIZED INGESTION ---

    async def ingest_sql_view(self, doc_id: UUID, connector: Connector):
        """
        Ingests a SQL View by extracting its schema description and vectorizing it.
        This allows the RAG system to find this table when answering questions.
        """
        start_time = time.time()
        logger.info(f"Orchestrating SQL ingestion for Doc {doc_id}")

        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        if not self.sql_discovery_service:
            raise TechnicalError("SQL Discovery Service not injected into Orchestrator")

        try:
            # 1. Update status
            await self.doc_repo.update(doc.id, {"status": DocStatus.PROCESSING})
            await manager.emit_document_update(str(doc.id), DocStatus.PROCESSING, "Extracting Schema...")

            # 2. Extract or Use Pre-stored Schema
            view_name = doc.file_name

            # OPTIMIZATION: For Vanna SQL, DDL is stored in metadata
            file_metadata = doc.file_metadata or {}
            stored_ddl = file_metadata.get("ddl")

            if stored_ddl:
                logger.info(f"Using pre-stored DDL for {view_name} (Vanna SQL)")
                markdown_content = stored_ddl
            else:
                # Standard SQL: Generate DDL dynamically
                logger.info(f"Generating DDL dynamically for {view_name} (Standard SQL)")
                markdown_content = await self.sql_discovery_service.get_view_schema_markdown(connector, view_name)

            # 3. Create LlamaDocument
            import hashlib

            from llama_index.core import Document as LlamaDocument

            # Deterministic ID for cache
            stable_key = f"sql_view:{connector.id}:{view_name}"
            unique_id = hashlib.md5(stable_key.encode()).hexdigest()

            llama_doc = LlamaDocument(
                text=markdown_content,
                id_=unique_id,
                metadata={
                    "connector_id": str(connector.id),
                    "connector_document_id": str(doc.id),
                    "file_name": view_name,
                    "type": "sql_view_schema",
                    "connector_acl": ["system:sql_schema"],  # Separate ACL for Router access only
                },
                excluded_llm_metadata_keys=["connector_id", "connector_document_id", "type", "connector_acl"],
                metadata_separator="\n",
            )

            # 4. Run Pipeline
            pipeline, vector_store, _, workers, _, docstore = await self.setup_pipeline(connector)

            logger.info(f"Computing embeddings for SQL Schema: {view_name}")

            nodes = await pipeline.arun(
                documents=[llama_doc], num_workers=0, show_progress=False  # Force sync for safety with specialized docs
            )

            total_chunks = len(nodes)
            token_count = sum(len(n.get_content()) for n in nodes)

            # P0 FIX: Self-Healing Stats for Cache Hits (Nodes empty if cached)
            if total_chunks == 0:
                try:
                    provider = connector.configuration.get("ai_provider")
                    collection = await self.vector_service.get_collection_name(provider)
                    total_chunks = await self.vector_repo.count_by_document_id(collection, doc.id)
                    if total_chunks > 0:
                        logger.info(
                            f"💾 CACHE HIT | Recovered {total_chunks} vectors from Qdrant for SQL View {doc.id}"
                        )
                        # Estimate tokens? Hard without content, keep 0 or fetch.
                except Exception as e:
                    logger.warning(f"Failed to recover vector count for {doc.id}: {e}")

            # 5. Update Stats & Success
            elapsed_ms = (time.time() - start_time) * 1000
            now = datetime.now()

            await self.doc_repo.update(
                doc.id,
                {
                    "chunks_total": total_chunks,
                    "chunks_processed": total_chunks,
                    "vector_point_count": total_chunks,
                    "doc_token_count": token_count,
                    "status": DocStatus.INDEXED,
                    "last_vectorized_at": now,
                    "processing_duration_ms": elapsed_ms,
                },
            )

            await manager.emit_document_update(
                str(doc.id),
                DocStatus.INDEXED,
                "Schema Vectorized",
                doc_token_count=token_count,
                vector_point_count=total_chunks,
                last_vectorized_at=now,
                processing_duration_ms=elapsed_ms,
            )

            # Persist Cache
            try:
                cache_dir = Path(".cache") / "ingestion" / str(connector.id)
                if hasattr(pipeline, "cache") and pipeline.cache:
                    doc_path = cache_dir / "docstore.json"
                    kv_path = cache_dir / "kv_store.json"
                    if hasattr(pipeline.cache.cache, "persist"):
                        pipeline.cache.cache.persist(str(kv_path))
                    if docstore:
                        docstore.persist(str(doc_path))
            except:
                pass

            logger.info(f"SQL Ingestion SUCCESS | {view_name}")

        except Exception as e:
            logger.error(f"SQL Ingestion FAILED | {doc_id} | {e}", exc_info=True)
            await self.doc_repo.update(doc.id, {"status": DocStatus.FAILED, "error_message": str(e)})
            raise e

    async def _process_smart_batch(
        self,
        texts: List[str],
        metadatas: List[dict],
        doc,
        connector,
        embed_model,
        collection_name,
        connector_acl: list = None,
    ) -> int:
        """
        Processes a pre-transformed batch (Smart Strategy).
        """
        if not texts:
            return 0

        # Inject ACLs if not present (Transformer handles payload, but ACL is system-level)
        for meta in metadatas:
            meta["connector_id"] = str(connector.id)
            meta["connector_document_id"] = str(doc.id)
            meta["connector_acl"] = connector_acl or []

        # 1. Async Embedding
        embeddings = await embed_model.aget_text_embedding_batch(texts)

        # 2. Point Creation
        points = []
        for i, text in enumerate(texts):
            # Deterministic ID using LINE NUMBER (injected by transformer)
            # This is the "Magic Fix" for 1-to-1 mapping
            line_num = metadatas[i].get("_line_number", i)
            point_id = hashlib.md5(f"{doc.id}_line_{line_num}".encode()).hexdigest()

            # LlamaIndex Schema Compliance:
            # 1. Flat Payload: Used for Qdrant Filters (e.g. make="Ford")
            # 2. _node_content: Used for LlamaIndex Node reconstruction. MUST include metadata inside to populate node.metadata.
            node_content = {"text": text, "metadata": metadatas[i]}  # P0 FIX: Duplicate metadata here for LlamaIndex

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[i],
                    payload={**metadatas[i], "_node_content": json.dumps(node_content)},
                )
            )

        # 3. Vector DB Upsert (Blocking I/O Protection)
        await self.vector_repo.upsert_points(collection_name=collection_name, points=points)

        return sum(len(t) for t in texts)

    async def _process_batch_async(
        self, records: List[dict], schema, doc, connector, embed_model, collection_name, connector_acl: list = None
    ) -> int:
        """
        Legacy batch processor (kept for backward compatibility or direct calls).
        Refactored to delegate to _process_smart_batch?
        Actually, simpler to keep separate or deprecate.
        For now, let's leave it as "Classic Mode" fallback if needed.
        """
        # ... (Old logic, but we won't use it in new flow)
        pass

    # --- HELPERS ---

    @staticmethod
    async def _run_blocking_io(func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _get_connector_status(self, cid: UUID) -> ConnectorStatus:
        connector = await self.connector_repo.get_by_id(cid)
        return connector.status if connector else ConnectorStatus.ERROR
