"""
Unit tests for backend/app/schemas/enums.py
Tests cover enum definitions, string values, and serialization compatibility.
"""

import pytest
from app.schemas.enums import (
    ConnectorStatus,
    ConnectorType,
    DocStatus,
    NotificationType,
    ScheduleType,
    UserRole,
)


class TestConnectorStatus:
    """Test ConnectorStatus enum."""

    def test_all_values_are_strings(self):
        """Ensure all enum values are strings (for JSON serialization)."""
        for status in ConnectorStatus:
            assert isinstance(status.value, str)

    def test_active_statuses(self):
        """Test active connector statuses."""
        assert ConnectorStatus.CREATED == "created"
        assert ConnectorStatus.IDLE == "idle"
        assert ConnectorStatus.QUEUED == "queued"
        assert ConnectorStatus.SYNCING == "syncing"
        assert ConnectorStatus.ERROR == "error"
        assert ConnectorStatus.PAUSED == "paused"

    def test_legacy_statuses(self):
        """Test legacy connector statuses (backward compatibility)."""
        assert ConnectorStatus.STARTING == "starting"
        assert ConnectorStatus.VECTORIZING == "vectorizing"

    def test_enum_membership(self):
        """Test that string values can be used to get enum members."""
        assert ConnectorStatus("idle") == ConnectorStatus.IDLE
        assert ConnectorStatus("syncing") == ConnectorStatus.SYNCING


class TestConnectorType:
    """Test ConnectorType enum."""

    def test_all_values_are_strings(self):
        """Ensure all enum values are strings."""
        for connector_type in ConnectorType:
            assert isinstance(connector_type.value, str)

    def test_connector_types(self):
        """Test all connector types."""
        assert ConnectorType.LOCAL_FILE == "local_file"
        assert ConnectorType.LOCAL_FOLDER == "local_folder"
        assert ConnectorType.SQL == "sql"
        assert ConnectorType.VANNA_SQL == "vanna_sql"

    def test_enum_membership(self):
        """Test that string values can be used to get enum members."""
        assert ConnectorType("sql") == ConnectorType.SQL
        assert ConnectorType("vanna_sql") == ConnectorType.VANNA_SQL


class TestScheduleType:
    """Test ScheduleType enum."""

    def test_all_values_are_strings(self):
        """Ensure all enum values are strings."""
        for schedule_type in ScheduleType:
            assert isinstance(schedule_type.value, str)

    def test_schedule_types(self):
        """Test all schedule types."""
        assert ScheduleType.MANUAL == "manual"
        assert ScheduleType.CRON == "cron"

    def test_enum_membership(self):
        """Test that string values can be used to get enum members."""
        assert ScheduleType("manual") == ScheduleType.MANUAL
        assert ScheduleType("cron") == ScheduleType.CRON


class TestDocStatus:
    """Test DocStatus enum."""

    def test_all_values_are_strings(self):
        """Ensure all enum values are strings."""
        for status in DocStatus:
            assert isinstance(status.value, str)

    def test_doc_statuses(self):
        """Test all document statuses."""
        assert DocStatus.IDLE == "idle"
        assert DocStatus.PENDING == "pending"
        assert DocStatus.PROCESSING == "processing"
        assert DocStatus.INDEXING == "indexing"
        assert DocStatus.INDEXED == "indexed"
        assert DocStatus.FAILED == "failed"
        assert DocStatus.SKIPPED == "skipped"
        assert DocStatus.PAUSED == "paused"
        assert DocStatus.UNSUPPORTED == "unsupported"

    def test_enum_membership(self):
        """Test that string values can be used to get enum members."""
        assert DocStatus("indexed") == DocStatus.INDEXED
        assert DocStatus("failed") == DocStatus.FAILED


class TestNotificationType:
    """Test NotificationType enum."""

    def test_all_values_are_strings(self):
        """Ensure all enum values are strings."""
        for notification_type in NotificationType:
            assert isinstance(notification_type.value, str)

    def test_notification_types(self):
        """Test all notification types."""
        assert NotificationType.INFO == "info"
        assert NotificationType.SUCCESS == "success"
        assert NotificationType.WARNING == "warning"
        assert NotificationType.ERROR == "error"
        assert NotificationType.SYSTEM == "system"

    def test_enum_membership(self):
        """Test that string values can be used to get enum members."""
        assert NotificationType("error") == NotificationType.ERROR
        assert NotificationType("success") == NotificationType.SUCCESS


class TestUserRole:
    """Test UserRole enum."""

    def test_all_values_are_strings(self):
        """Ensure all enum values are strings."""
        for role in UserRole:
            assert isinstance(role.value, str)

    def test_user_roles(self):
        """Test all user roles."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.USER == "user"

    def test_enum_membership(self):
        """Test that string values can be used to get enum members."""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("user") == UserRole.USER


class TestEnumEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_enum_value_raises_error(self):
        """Test that invalid enum values raise ValueError."""
        with pytest.raises(ValueError):
            ConnectorStatus("invalid_status")

        with pytest.raises(ValueError):
            DocStatus("nonexistent")

        with pytest.raises(ValueError):
            UserRole("superadmin")

    def test_enum_comparison(self):
        """Test enum comparison works correctly."""
        assert ConnectorStatus.IDLE == ConnectorStatus.IDLE
        assert ConnectorStatus.IDLE != ConnectorStatus.SYNCING
        assert DocStatus.INDEXED != DocStatus.FAILED

    def test_enum_in_list(self):
        """Test enum membership in lists (common use case in production)."""
        active_statuses = [ConnectorStatus.SYNCING, ConnectorStatus.QUEUED]
        assert ConnectorStatus.SYNCING in active_statuses
        assert ConnectorStatus.IDLE not in active_statuses

    def test_enum_iteration(self):
        """Test that enums can be iterated (useful for validation)."""
        all_connector_statuses = list(ConnectorStatus)
        assert len(all_connector_statuses) == 8  # 6 active + 2 legacy

        all_user_roles = list(UserRole)
        assert len(all_user_roles) == 2
