import logging
from typing import List

from llama_index.core.schema import Document
from llama_index.readers.microsoft_sharepoint import SharePointReader

from app.core.exceptions import ExternalDependencyError
from app.core.interfaces.base_connector import BaseConnector
from app.schemas.ingestion import SharePointIngestionConfig

logger = logging.getLogger(__name__)


class SharePointConnector(BaseConnector):
    """
    Connector for Microsoft SharePoint Online (Graph API).
    """

    async def validate_config(self, config: SharePointIngestionConfig) -> bool:
        """
        Validate connector configuration.
        """
        if not config.client_id:
            raise ValueError("Client ID is required.")
        if not config.client_secret:
            raise ValueError("Client Secret is required.")
        if not config.tenant_id:
            raise ValueError("Tenant ID is required.")
        return True

    async def load_data(self, config: SharePointIngestionConfig) -> List[Document]:
        """
        Load documents from SharePoint.
        """
        logger.info(f"Starting SharePoint ingestion from Tenant {config.tenant_id}")

        try:
            loader = SharePointReader(
                client_id=config.client_id, client_secret=config.client_secret, tenant_id=config.tenant_id
            )

            # Load Data
            # Note: The underlying reader handles the Graph API calls.
            # We map our config to its expected arguments.
            documents = loader.load_data(
                sharepoint_site_name=config.sharepoint_site_name,
                sharepoint_folder_path=config.folder_path,
                recursive=config.recursive,
            )

            logger.info(f"SharePoint ingestion complete. Loaded {len(documents)} documents.")

            # Post-processing: Add Source Type and URL metadata
            for doc in documents:
                doc.metadata["source_type"] = "sharepoint"
                doc.metadata["tenant_id"] = config.tenant_id
                if config.sharepoint_site_name:
                    doc.metadata["site_name"] = config.sharepoint_site_name

                # Ensure web_url is preserved if the reader provides it (usually in metadata)
                # If not, we can't easily reconstruction it without more info, but Graph usually provides 'webUrl'

            return documents

        except ImportError:
            raise ExternalDependencyError(
                "Missing dependency 'llama-index-readers-microsoft-sharepoint'. Please install it.",
                error_code="DEPENDENCY_MISSING",
            )
        except Exception as e:
            logger.error(f"SharePoint Ingestion Failed: {e}", exc_info=True)
            raise ExternalDependencyError(f"Failed to ingest from SharePoint: {e}")
