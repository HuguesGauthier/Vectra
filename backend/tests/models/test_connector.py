"""
Unit tests for backend/app/models/connector.py

Tests cover:
- Happy path: Valid Connector creation
- Defaults: Verifying default values (status, schedule_type)
- JSON Field: Verifying configuration dict persistence
"""

from uuid import UUID

from app.models.connector import Connector
from app.schemas.enums import ConnectorStatus, ConnectorType, ScheduleType


class TestConnector:
    """Test suite for Connector model."""

    # ========== HAPPY PATH ==========

    def test_create_valid_connector(self):
        """Test creating a valid Connector instance."""
        connector = Connector(
            name="My PDF Connector",
            connector_type=ConnectorType.LOCAL_FILE,
            configuration={"path": "/tmp/doc.pdf"},
            schedule_type=ScheduleType.MANUAL,
        )

        assert connector.name == "My PDF Connector"
        assert connector.connector_type == ConnectorType.LOCAL_FILE
        assert connector.configuration == {"path": "/tmp/doc.pdf"}
        assert connector.schedule_type == ScheduleType.MANUAL
        assert connector.status == ConnectorStatus.IDLE  # Default
        assert isinstance(connector.id, UUID)
        assert connector.chunk_size == 300  # Default
        assert connector.chunk_overlap == 30  # Default

    def test_create_connector_with_defaults(self):
        """Test creating Connector with minimal fields (relying on defaults)."""
        connector = Connector(
            name="Minimal Connector",
            connector_type=ConnectorType.SQL,
        )

        assert connector.name == "Minimal Connector"
        assert connector.connector_type == ConnectorType.SQL
        assert connector.configuration == {}  # Default factory
        assert connector.schedule_type == ScheduleType.MANUAL  # Default
        assert connector.status == ConnectorStatus.IDLE

    # ========== DATA INTEGRITY ==========

    def test_json_configuration_field(self):
        """Test configuration field accepts complex dictionary (JSON)."""
        config = {"url": "https://example.com", "recursive": True, "headers": {"User-Agent": "Bot"}, "max_depth": 5}

        connector = Connector(
            name="Web Crawler", connector_type=ConnectorType.SQL, configuration=config  # Just using a type
        )

        assert connector.configuration == config
        assert connector.configuration["max_depth"] == 5

    def test_chunking_config(self):
        """Test overriding chunking configuration."""
        connector = Connector(
            name="Special Chunking", connector_type=ConnectorType.LOCAL_FILE, chunk_size=1000, chunk_overlap=100
        )

        assert connector.chunk_size == 1000
        assert connector.chunk_overlap == 100

    def test_analytics_counters(self):
        """Test analytics counters default to 0."""
        connector = Connector(name="Analytics Test", connector_type=ConnectorType.LOCAL_FILE)

        assert connector.total_docs_count == 0
        assert connector.indexed_docs_count == 0
        assert connector.failed_docs_count == 0
