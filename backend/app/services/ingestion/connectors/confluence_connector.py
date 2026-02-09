import logging
import os
from typing import List, Optional

from llama_index.core.schema import Document
from llama_index.readers.confluence import ConfluenceReader

from app.core.exceptions import ConfigurationError, ExternalDependencyError
from app.core.interfaces.base_connector import BaseConnector
from app.schemas.ingestion import ConfluenceIngestionConfig

logger = logging.getLogger(__name__)


class ConfluenceConnector(BaseConnector):
    """
    Connector for Atlassian Confluence.
    Uses 'llama-index-readers-confluence' to crawl pages via API.
    """

    async def validate_config(self, config: ConfluenceIngestionConfig) -> bool:
        """
        Validate connector configuration.
        """
        if not config.url or not config.url.startswith("http"):
            raise ValueError("Confluence URL must be a valid HTTP/HTTPS URL.")
        if not config.username or "@" not in config.username:
            raise ValueError("Username must be a valid email address.")
        if not config.api_token:
            raise ValueError("API Token is required.")
        return True

    async def load_data(self, config: ConfluenceIngestionConfig) -> List[Document]:
        """
        Load documents from Confluence.

        Args:
            config: ConfluenceIngestionConfig with url, user, token, etc.

        Returns:
            List[Document]: Extracted pages and attachments.
        """
        logger.info(f"Starting Confluence ingestion from {config.url} (Space: {config.space_key or 'ALL'})")

        try:
            # Initialize Reader
            # Note: ConfluenceReader expects base_url without /wiki/rest/api usually, or handles it.
            # LlamaIndex ConfluenceReader uses standard atlassian-python-api under hood usually.
            reader = ConfluenceReader(
                base_url=config.url,
                user_name=config.username,
                password_or_token=config.api_token,
                cloud=True,  # Default to Cloud for now
            )

            # Metadata extraction is handled by Reader, but we can enhance if needed.

            # Load Data
            # If space_key is provided, valid. If None, it might try to load everything (dangerous).
            # The interface allows space_key=None, but for safety we might warn.

            if config.space_key:
                documents = reader.load_data(space_key=config.space_key, include_attachments=config.include_attachments)
            else:
                # If no space key, load everything? Or is page_ids required?
                # Reader.load_data takes page_ids, space_key, or cql.
                # If nothing provided, it might default to ALL spaces or fail.
                # Let's assume user wants everything if space_key is None (Power User mode).
                logger.warning("No space_key provided. Attempting to ingest ALL spaces.")
                documents = reader.load_data(include_attachments=config.include_attachments)

            logger.info(f"Confluence ingestion complete. Loaded {len(documents)} documents.")

            # Post-processing: Add Source Type
            for doc in documents:
                doc.metadata["source_type"] = "confluence"
                doc.metadata["confluence_url"] = config.url
                if config.space_key:
                    doc.metadata["space_key"] = config.space_key

            return documents

        except ImportError:
            raise ExternalDependencyError(
                "Missing dependency 'llama-index-readers-confluence'. Please install it.",
                error_code="DEPENDENCY_MISSING",
            )
        except Exception as e:
            logger.error(f"Confluence Ingestion Failed: {e}", exc_info=True)
            raise ExternalDependencyError(f"Failed to ingest from Confluence: {e}")
