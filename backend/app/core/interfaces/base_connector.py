"""
Base interface for all connector implementations.

All connectors must implement this interface to ensure:
- Async-first design (non-blocking IO)
- Strong typing via generic TConfig
- Proper validation before data loading

Security Notes:
- Implementations MUST validate paths to prevent traversal attacks
- Network connectors MUST implement SSRF protection
- All blocking I/O MUST use asyncio.to_thread()
"""

import os
from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from llama_index.core.schema import Document

# Generic type for connector-specific configuration
TConfig = TypeVar("TConfig")


class BaseConnector(ABC, Generic[TConfig]):
    """
    Abstract base class for all data source connectors.

    Type Parameters:
        TConfig: Pydantic model defining connector configuration schema
    """

    @abstractmethod
    async def load_data(self, config: TConfig) -> List[Document]:
        """
        Load documents from the data source.

        Args:
            config: Validated configuration object

        Returns:
            List of LlamaIndex Document objects

        Raises:
            ValueError: For invalid configuration
            FileSystemError: For file access issues
            TechnicalError: For other errors
        """
        pass

    @abstractmethod
    async def validate_config(self, config: TConfig) -> bool:
        """
        Validate connector configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass


# === CONNECTOR UTILITIES ===


def get_full_path_from_connector(connector, doc_file_path: str) -> str:
    """
    Reconstruct full file path based on connector type and configuration.

    This is a domain helper for the Connector subsystem.
    Used by SystemService, Orchestrator, and IngestionService.

    Logic:
    - **Folder connectors**: configuration.path is the base directory
      - Example: path="D:\\Documents", file_path="RH\\procedure.docx"
      - Result: "D:\\Documents\\RH\\procedure.docx"

    - **File connectors**: configuration.path IS the full file path
      - Example: path="D:\\Important\\budget.xlsx", file_path="budget.xlsx"
      - Result: "D:\\Important\\budget.xlsx" (ignore file_path)

    Args:
        connector: Connector model with type and configuration
        doc_file_path: Relative file path from document record

    Returns:
        Absolute path to the file
    """
    base_path = connector.configuration.get("path", "")
    if not base_path:
        return doc_file_path

    conn_type = str(connector.connector_type).strip().lower()

    # For file connectors, path IS the complete file path
    if conn_type in {"file", "local_file"}:
        return base_path

    # Security (P0): Prevent path traversal
    # Ensure relative path doesn't escape base_path
    resolved_base = os.path.abspath(base_path)

    # Strip leading separators and normalize
    safe_rel_path = doc_file_path.lstrip("/\\")
    full_path = os.path.abspath(os.path.join(resolved_base, safe_rel_path))

    if not full_path.startswith(resolved_base):
        import logging

        logging.getLogger(__name__).warning(
            f"🚨 [SECURITY] Path traversal attempt blocked: {doc_file_path} (Context: {resolved_base})"
        )
        # Fallback to joining only the filename to the base path for safety
        return os.path.join(resolved_base, os.path.basename(doc_file_path))

    return full_path
