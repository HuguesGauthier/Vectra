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


def translate_host_path(path: str) -> str:
    """
    Translates a host Windows path to a container Linux path based on VECTRA_DATA_PATH.
    Example: D:/Docs/RH -> /data/docs/RH (if VECTRA_DATA_PATH=D:/Docs)
    """
    import sys
    from app.core.settings import settings

    if sys.platform == "win32":
        return path

    if not path:
        return path

    # Case 1: Running in Docker (Linux)
    # We need to recognize the HOST path prefix and replace it with /data
    # VECTRA_DATA_PATH_HOST is the host-side path (e.g. H:/)
    # VECTRA_DATA_PATH is the container-side path (e.g. /data)
    host_prefix = settings.VECTRA_DATA_PATH_HOST or settings.VECTRA_DATA_PATH

    if not host_prefix:
        return path

    # Normalize both paths to forward slashes for cross-platform comparison
    norm_host_prefix = host_prefix.replace("\\", "/").rstrip("/").lower()
    norm_input_path = path.replace("\\", "/").lower()

    if norm_input_path.startswith(norm_host_prefix):
        # Replace the host prefix with /data
        # We preserve the original case of the suffix
        rel_to_root = path.replace("\\", "/")[len(norm_host_prefix) :].lstrip("/")
        translated = os.path.join("/data", rel_to_root).replace("\\", "/")

        import logging

        logging.getLogger(__name__).info(f"📂 [PATH_TRANSLATION] {path} -> {translated}")
        return translated

    import logging

    logging.getLogger(__name__).debug(
        f"📂 [NO_TRANSLATION] '{norm_input_path}' does not start with '{norm_host_prefix}'"
    )
    return path


def get_full_path_from_connector(connector, doc_file_path: str) -> str:
    """
    Reconstruct full file path based on connector type and configuration.
    Handles dynamic path translation for Docker environments.
    """
    base_path = connector.configuration.get("path", "")
    if not base_path:
        return doc_file_path

    # Apply translation
    base_path = translate_host_path(base_path)

    conn_type = str(connector.connector_type).strip().lower()
    # For file connectors, path IS the complete file path
    if conn_type in {"file", "local_file"}:
        return base_path

    # Security (P0): Prevent path traversal
    resolved_base = os.path.abspath(base_path)
    safe_rel_path = doc_file_path.lstrip("/\\")
    full_path = os.path.abspath(os.path.join(resolved_base, safe_rel_path))

    if not full_path.startswith(resolved_base):
        import logging

        logging.getLogger(__name__).warning(
            f"🚨 [SECURITY] Path traversal attempt blocked: {doc_file_path} (Context: {resolved_base})"
        )
        return os.path.join(resolved_base, os.path.basename(doc_file_path))

    return full_path
