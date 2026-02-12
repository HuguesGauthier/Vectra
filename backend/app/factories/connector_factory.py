"""
ConnectorFactory - Encapsulates all connector domain logic.

Responsibilities:
- Instantiate appropriate connector based on type
- Map configuration to Pydantic schemas
- Load documents from connector
- Provide one-stop method for IngestionService

Architecture:
- Uses Strategy Pattern (CONFIG_SCHEMAS dict)
- Hides connector implementation details from service layer
"""

from typing import List

from llama_index.core.schema import Document

from app.core.interfaces.base_connector import BaseConnector
from app.models.enums import ConnectorType
from app.schemas.ingestion import FileIngestionConfig, FolderIngestionConfig, SqlIngestionConfig
from app.services.ingestion.connectors.file_connector import FileConnector
from app.services.ingestion.connectors.folder_connector import FolderConnector
from app.services.ingestion.connectors.sql_connector import SqlConnector

# Strategy Pattern: Config schema mapping
CONFIG_SCHEMAS = {
    ConnectorType.LOCAL_FILE: FileIngestionConfig,
    ConnectorType.LOCAL_FOLDER: FolderIngestionConfig,
    ConnectorType.SQL: SqlIngestionConfig,
}


class ConnectorFactory:
    """
    Factory for creating and using connectors.

    Encapsulates all connector domain logic:
    - Type detection
    - Connector instantiation
    - Configuration mapping
    - Data loading
    """

    @staticmethod
    def get_connector(source_type: str | ConnectorType) -> BaseConnector:
        """
        Get connector instance by type.

        Args:
            source_type: Type of connector
        """
        # Normalize to enum if string
        if isinstance(source_type, str):
            try:
                source_type = ConnectorType(source_type.strip().lower())
            except ValueError:
                raise ValueError(f"Unknown source type: {source_type}")

        if source_type == ConnectorType.LOCAL_FILE:
            return FileConnector()
        elif source_type == ConnectorType.LOCAL_FOLDER:
            return FolderConnector()
        elif source_type == ConnectorType.SQL:
            return SqlConnector()
        else:
            raise ValueError(f"Unsupported connector implementation for type: {source_type}")

    @staticmethod
    async def load_documents(connector_model) -> List[Document]:
        """
        One-stop method to load documents from a connector.

        Encapsulates the entire connector workflow:
        1. Detect connector type
        2. Instantiate appropriate connector
        3. Build and validate configuration
        4. Load documents

        This is the ONLY method IngestionService should call.

        Args:
            connector_model: Connector ORM model with type and configuration

        Returns:
            List of LlamaIndex Document objects

        Raises:
            ValueError: If connector type is unsupported or config is invalid
            Exception: Any errors from connector.load_data()
        """
        # 1. Detect type
        raw_type = str(connector_model.connector_type).strip().lower()
        try:
            conn_type = ConnectorType(raw_type)
        except ValueError:
            raise ValueError(f"Unsupported connector type: {raw_type}")

        # 2. Instantiate connector
        plugin = ConnectorFactory.get_connector(conn_type)

        # 3. Build config (Strategy Pattern)
        config = ConnectorFactory._build_config(conn_type, connector_model.configuration)

        # 4. Load data
        return await plugin.load_data(config)

    @staticmethod
    def _build_config(conn_type: ConnectorType, config_data: dict):
        """
        Build typed Pydantic config from raw dict.

        Args:
            conn_type: Connector type
            config_data: Raw configuration dict

        Returns:
            Pydantic config instance

        Raises:
            ValueError: If type is unsupported or validation fails
        """
        if conn_type not in CONFIG_SCHEMAS:
            raise ValueError(f"No config schema for type: {conn_type}")

        config_class = CONFIG_SCHEMAS[conn_type]
        config_dict = dict(config_data)

        # PURE CODE: No legacy normalization.
        # The frontend/client must send data matching the Pydantic schema exactly.

        try:
            return config_class(**config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration for {conn_type}: {e}")
