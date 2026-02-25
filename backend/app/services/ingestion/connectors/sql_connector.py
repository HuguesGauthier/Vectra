from typing import List

from llama_index.core import Document
from pydantic import BaseModel

from app.core.interfaces.base_connector import BaseConnector
from app.schemas.ingestion import BaseIngestionConfig, SqlIngestionConfig


class SqlConnector(BaseConnector[SqlIngestionConfig]):
    """
    Placeholder connector for SQL databases.

    SQL connectors work differently from file-based connectors:
    - They store connection configuration
    - They don't scan files or load documents during creation
    - Document loading will be handled by a future SQL ingestion pipeline

    This is a placeholder to allow SQL connectors to be created
    without triggering the standard document loading flow.
    """

    async def validate_config(self, config: SqlIngestionConfig) -> bool:
        """
        Validates SQL connection configuration.

        Checks that all required fields are present.
        """
        required_fields = ["host", "port", "database", "user", "password"]
        missing = [f for f in required_fields if not getattr(config, f, None)]

        if missing:
            raise ValueError(f"Missing required SQL configuration fields: {', '.join(missing)}")

        return True

    async def load_data(self, config: SqlIngestionConfig) -> List[Document]:
        """
        SQL connectors don't load documents during creation.

        Returns empty list. SQL data will be ingested through
        a separate pipeline that queries views/tables.

        This method exists to satisfy the BaseConnector interface.
        """
        # SQL connectors are created for configuration storage only
        # Actual data ingestion happens through separate SQL pipeline
        return []
