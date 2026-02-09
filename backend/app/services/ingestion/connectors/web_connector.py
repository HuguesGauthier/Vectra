import asyncio
import socket
from typing import List
from urllib.parse import urlparse

from llama_index.core import Document

from app.core.interfaces.base_connector import BaseConnector
from app.schemas.ingestion import WebIngestionConfig

# Lazy import
try:
    from llama_index.readers.web import TrafilaturaWebReader
except ImportError:
    TrafilaturaWebReader = None


class WebConnector(BaseConnector[WebIngestionConfig]):
    """
    Connector for ingesting web content.

    Security: SSRF checks on URLs.
    Performance: Async wrapper for network requests.
    """

    async def validate_config(self, config: WebIngestionConfig) -> bool:
        if not config.url.startswith("http"):
            return False

        # P0: SSRF Protection (Basic)
        # Prevent access to localhost, 127.0.0.1, 0.0.0.0
        try:
            parsed = urlparse(config.url)
            hostname = parsed.hostname
            if not hostname:
                return False

            # Allow list or Block list logic
            if hostname in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
                return False

            # Advanced: Resolve DNS and check if private IP (omitted for brevity but recommended)
            return True
        except Exception:
            return False

    async def load_data(self, config: WebIngestionConfig) -> List[Document]:
        if not await self.validate_config(config):
            raise ValueError(f"Invalid or unsafe configuration: {config.url}")

        if TrafilaturaWebReader is None:
            raise ImportError("TrafilaturaWebReader is not available. Please install `llama-index-readers-web`.")

        def _load_sync():
            loader = TrafilaturaWebReader()
            return loader.load_data(urls=[config.url])

        try:
            return await asyncio.to_thread(_load_sync)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch content from {config.url}: {str(e)}") from e
