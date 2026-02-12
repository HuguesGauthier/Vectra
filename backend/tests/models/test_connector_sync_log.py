"""
Unit tests for backend/app/models/connector_sync_log.py

Tests cover:
- Happy path: Valid ConnectorSyncLog creation
- Defaults: Verifying default values
- Indexes: verifying index definitions
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Index

from app.models.connector_sync_log import ConnectorSyncLog


class TestConnectorSyncLog:
    """Test suite for ConnectorSyncLog model."""

    # ========== HAPPY PATH ==========

    def test_create_valid_sync_log(self):
        """Test creating a valid ConnectorSyncLog instance."""
        connector_id = uuid4()

        log = ConnectorSyncLog(
            connector_id=connector_id, status="success", documents_synced=100, sync_duration=15.5, error_message=None
        )

        assert log.connector_id == connector_id
        assert log.status == "success"
        assert log.documents_synced == 100
        assert log.sync_duration == 15.5
        assert log.error_message is None
        assert isinstance(log.id, UUID)
        # sync_time has server_default/default factory behavior check
        # In pure python init, it might be missed if strictly server_default
        # But we can verify it's a field.

    def test_defaults(self):
        """Test default values."""
        connector_id = uuid4()
        log = ConnectorSyncLog(connector_id=connector_id, status="status_check")

        assert log.documents_synced == 0
        assert log.error_message is None
        assert log.sync_duration is None

    # ========== CONSTRAINTS & INDEXES ==========

    def test_indexes_exist(self):
        """Verify that the Indexes are defined in __table_args__."""
        table_args = ConnectorSyncLog.__table_args__

        # We expect a tuple of Index objects
        index_names = []
        for arg in table_args:
            if isinstance(arg, Index):
                index_names.append(arg.name)

        assert "ix_connector_sync_logs_connector_time" in index_names
        assert "ix_connector_sync_logs_status_time" in index_names

    # ========== EDGE CASES ==========

    def test_documents_synced_types(self):
        """Test types for documents_synced."""
        connector_id = uuid4()
        log = ConnectorSyncLog(connector_id=connector_id, status="partial", documents_synced=50)
        assert log.documents_synced == 50

    def test_error_message_storage(self):
        """Test storing error message."""
        connector_id = uuid4()
        error_msg = "Connection timeout after 30s"
        log = ConnectorSyncLog(connector_id=connector_id, status="failure", error_message=error_msg)
        assert log.error_message == error_msg
