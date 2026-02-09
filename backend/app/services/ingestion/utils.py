import asyncio
import logging
import mimetypes
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.core.exceptions import (FileSystemError, FunctionalError,
                                 TechnicalError)
from app.models.connector_document import ConnectorDocument

logger = logging.getLogger(__name__)


class IngestionUtils:

    # Constants for clarity and performance
    MIME_FALLBACK_MAP = {
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimates tokens using the standard 4-char heuristic.
        """
        if not text:
            return 0
        return len(text) // 4

    @staticmethod
    def detect_mime_type(file_path: str) -> str:
        """
        Robust MIME type detection.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext in IngestionUtils.MIME_FALLBACK_MAP:
            return IngestionUtils.MIME_FALLBACK_MAP[ext]

        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                return mime_type
        except Exception as e:
            logger.debug(f"Mime type guess failed for {file_path}: {e}")
            pass

        return "application/octet-stream"

    @staticmethod
    def update_doc_metadata(doc: ConnectorDocument, full_path: str) -> None:
        """
        Updates document metadata from disk stats safely.
        """
        try:
            file_stat = os.stat(full_path)
            doc.file_size = file_stat.st_size
            doc.last_modified_at_source = datetime.fromtimestamp(file_stat.st_mtime)
            doc.mime_type = IngestionUtils.detect_mime_type(full_path)

            new_metadata = dict(doc.file_metadata) if doc.file_metadata else {}
            new_metadata["original_name"] = os.path.basename(full_path)
            doc.file_metadata = new_metadata

        except OSError as e:
            logger.warning(f"Could not read file stats for {full_path}: {e}")
        except Exception as e:
            logger.error(f"Metadata update error for {full_path}: {e}")

    @staticmethod
    async def validate_csv_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Async Wrapper for CSV Validation to prevent blocking the Event Loop.
        """
        return await asyncio.to_thread(IngestionUtils._validate_csv_file_sync, file_path)

    @staticmethod
    def _validate_csv_file_sync(file_path: str) -> List[Dict[str, Any]]:
        """
        Synchronous Implementation of CSV Validation.
        """
        func_name = "IngestionUtils.validate_csv_file"

        if not os.path.exists(file_path):
            raise FileSystemError(f"File not found: {file_path}", error_code="FILE_NOT_FOUND")

        try:
            # 1. Peek Header & Sample
            try:
                # Limit rows to avoid parsing huge files just for header check
                df_sample = pd.read_csv(file_path, nrows=10)
                full_columns = df_sample.columns.tolist()
                normalized_cols = [str(c).lower() for c in full_columns]
            except pd.errors.EmptyDataError:
                raise FunctionalError("CSV file is empty", error_code="CSV_EMPTY")
            except Exception as e:
                raise FunctionalError(f"Unreadable CSV Header: {e}", error_code="INVALID_CSV_FORMAT")

            # 2. Check Requirement: 'id' column

            id_real_name = None

            # Priority 1: Exact 'id'
            if "id" in normalized_cols:
                id_real_name = full_columns[normalized_cols.index("id")]

            # Priority 2: specific common ID names
            if not id_real_name:
                for col in full_columns:
                    if col.lower() in ["id_produit", "product_id", "code_produit"]:
                        id_real_name = col
                        break

            # Priority 3: looks like an ID
            if not id_real_name:
                for col in full_columns:
                    c_low = col.lower()
                    if c_low.startswith("id_") or c_low.endswith("_id"):
                        id_real_name = col
                        break

            if not id_real_name:
                raise FunctionalError(
                    message="CSV missing required 'id' column (or similar like id_produit)",
                    error_code="CSV_ID_COLUMN_MISSING",
                    details={"columns": full_columns},
                )

            # 3. Check Uniqueness (Optimized)
            seen_ids: Set[Any] = set()
            MAX_UNIQUE_IDS = 1_000_000  # Protection against Unbounded Memory

            try:
                chunk_iterator = pd.read_csv(file_path, usecols=[id_real_name], chunksize=5000)

                for chunk in chunk_iterator:
                    chunk_ids = chunk[id_real_name]

                    if not chunk_ids.is_unique:
                        raise FunctionalError("Duplicate IDs found in CSV", error_code="CSV_ID_DUPLICATE")

                    current_ids_set = set(chunk_ids.tolist())

                    if not current_ids_set.isdisjoint(seen_ids):
                        raise FunctionalError("Duplicate IDs found in CSV", error_code="CSV_ID_DUPLICATE")

                    if len(seen_ids) + len(current_ids_set) > MAX_UNIQUE_IDS:
                        logger.warning(
                            f"CSV too large for unique ID verification in RAM > {MAX_UNIQUE_IDS}. Skipping strict uniqueness check."
                        )
                        break

                    seen_ids.update(current_ids_set)

            except FunctionalError:
                raise
            except Exception as e:
                raise FunctionalError(f"Failed ID validation: {e}", error_code="INVALID_CSV_DATA")

            # 4. Infer Schema
            schema_info = []
            for col in full_columns:
                dtype = df_sample[col].dtype
                field_type = "string"
                if pd.api.types.is_numeric_dtype(dtype):
                    field_type = "number"

                sample_str = ""
                try:
                    unique_samples = df_sample[col].dropna().unique()
                    sample_str = ", ".join([str(s) for s in unique_samples[:3]])
                except:
                    pass

                schema_info.append(
                    {"name": col, "type": field_type, "description": f"Column {col} (e.g. {sample_str})"}
                )

            return schema_info

        except FunctionalError as fe:
            logger.warning(f"CSV Validation Failed: {fe.message}")
            raise fe
        except Exception as e:
            logger.error(f"Unexpected CSV Validation failure: {e}", exc_info=True)
            raise TechnicalError(f"System error validating CSV: {e}", error_code="CSV_SYS_ERROR")
