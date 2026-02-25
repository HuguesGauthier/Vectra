import pytest
from app.models.enums import ConnectorStatus, ConnectorType, ScheduleType
from app.schemas.enums import ConnectorStatus as SchemaStatus


class TestModelEnums:
    """
    Test suite for Model Enums to ensure they are correctly defined
    and compatible (by value) with Schema Enums, while being distinct classes.
    """

    def test_connector_status_values(self):
        """Ensure Model ConnectorStatus has correct values."""
        assert ConnectorStatus.IDLE == "idle"
        assert ConnectorStatus.SYNCING == "syncing"
        assert ConnectorStatus.CREATED == "created"

    def test_model_schema_compatibility(self):
        """
        Verify that Model and Schema enums are comparable by value (StrEnum behavior),
        but are distinct classes (Architecture requirement).
        """
        # Value equality
        assert ConnectorStatus.IDLE == SchemaStatus.IDLE
        assert ConnectorStatus.ERROR == SchemaStatus.ERROR

        # Class distinction
        assert ConnectorStatus is not SchemaStatus

    def test_connector_type_values(self):
        """Ensure Model ConnectorType has correct values."""
        assert ConnectorType.SQL == "sql"
        assert ConnectorType.LOCAL_FILE == "local_file"
        assert ConnectorType.LOCAL_FOLDER == "local_folder"
        assert ConnectorType.VANNA_SQL == "vanna_sql"

    def test_schedule_type_values(self):
        """Ensure Model ScheduleType has correct values."""
        assert ScheduleType.CRON == "cron"
        assert ScheduleType.MANUAL == "manual"
