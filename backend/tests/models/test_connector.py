"""
Tests for Connector model validation.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.connector import (ALLOWED_CONNECTOR_TYPES,
                                   ALLOWED_SCHEDULE_TYPES, ConnectorBase,
                                   ConnectorCreate, ConnectorUpdate)


class TestConnectorValidation:
    """Test validation rules."""

    def test_valid_connector_creation(self):
        """Valid connector should pass validation."""
        connector = ConnectorCreate(
            name="Test Connector", description="Test description", connector_type="local_file", schedule_type="manual"
        )
        assert connector.name == "Test Connector"
        assert connector.connector_type == "local_file"

    def test_invalid_connector_type_fails(self):
        """Invalid connector_type should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreate(name="Test", connector_type="invalid_type_xxx")
        assert "connector_type" in str(exc_info.value)

    def test_invalid_schedule_type_fails(self):
        """Invalid schedule_type should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreate(name="Test", connector_type="local_file", schedule_type="invalid_schedule")
        assert "schedule_type" in str(exc_info.value)

    def test_invalid_cron_expression_fails(self):
        """Invalid cron expression should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreate(name="Test", connector_type="local_file", schedule_cron="invalid cron")  # Only 2 fields
        assert "cron" in str(exc_info.value).lower()

    def test_valid_cron_expression(self):
        """Valid cron expression should pass."""
        connector = ConnectorCreate(
            name="Test", connector_type="local_file", schedule_cron="0 0 * * *"  # Daily at midnight
        )
        assert connector.schedule_cron == "0 0 * * *"

    def test_cron_with_suspicious_chars_fails(self):
        """Cron with suspicious characters should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreate(
                name="Test", connector_type="local_file", schedule_cron="0 0 * * *; rm -rf /"  # Injection attempt
            )
        # Validation catches field count first (7 fields instead of 5-6)
        assert "cron" in str(exc_info.value).lower()

    def test_empty_name_fails(self):
        """Empty name should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreate(name="", connector_type="local_file")
        assert "name" in str(exc_info.value).lower()

    def test_very_large_configuration_fails(self):
        """Configuration exceeding size limit should fail."""
        huge_config = {f"key_{i}": "x" * 1000 for i in range(200)}  # >100KB

        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreate(name="Test", connector_type="local_file", configuration=huge_config)
        assert "too large" in str(exc_info.value)

    def test_all_connector_types_valid(self):
        """All allowed connector types should be valid."""
        for conn_type in ALLOWED_CONNECTOR_TYPES:
            connector = ConnectorCreate(name=f"Test {conn_type}", connector_type=conn_type)
            assert connector.connector_type == conn_type


class TestConnectorUpdate:
    """Test update schema."""

    def test_partial_update_valid(self):
        """Partial updates should be valid."""
        update = ConnectorUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.connector_type is None

    def test_update_with_invalid_type_fails(self):
        """Update with invalid connector_type should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorUpdate(connector_type="invalid_type")
        assert "connector_type" in str(exc_info.value)

    def test_update_with_valid_cron(self):
        """Update with valid cron should work."""
        update = ConnectorUpdate(schedule_cron="*/5 * * * *")  # Every 5 minutes
        assert update.schedule_cron == "*/5 * * * *"
