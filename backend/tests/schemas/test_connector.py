import pytest
import json
from uuid import uuid4
from app.schemas.connector import (
    ConnectorCreate,
    ConnectorUpdate,
    ConnectorResponse,
    IndexingConfig,
    ConnectorType,
    ScheduleType,
    ConnectorStatus,
)


def test_connector_create_defaults():
    """Test default values in ConnectorCreate."""
    connector = ConnectorCreate(name="Test Connector", connector_type=ConnectorType.LOCAL_FOLDER)
    assert connector.name == "Test Connector"
    assert connector.is_enabled is True
    assert connector.chunk_size == 300
    assert connector.chunk_overlap == 30
    assert connector.schedule_type == ScheduleType.MANUAL
    assert connector.configuration == {}


def test_connector_dos_protection_config_size():
    """Test DoS protection for configuration size (100KB limit)."""
    # Create a large config that exceeds 100KB
    large_config = {"data": "x" * 101000}

    with pytest.raises(ValueError, match="Configuration too large"):
        ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER, configuration=large_config)


def test_connector_valid_config_size():
    """Test valid configuration size."""
    valid_config = {"key": "value", "nested": {"data": "test"}}
    connector = ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER, configuration=valid_config)
    assert connector.configuration == valid_config


def test_cron_validation_valid():
    """Test valid cron expressions."""
    # 5 fields
    connector = ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER, schedule_cron="0 0 * * *")
    assert connector.schedule_cron == "0 0 * * *"

    # 6 fields
    connector2 = ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER, schedule_cron="0 0 0 * * ?")
    assert connector2.schedule_cron == "0 0 0 * * ?"


def test_cron_validation_invalid_field_count():
    """Test cron validation rejects invalid field count."""
    with pytest.raises(ValueError, match="expected 5 or 6 fields"):
        ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER, schedule_cron="0 0 *")  # Only 3 fields


def test_cron_validation_invalid_characters():
    """Test cron validation rejects invalid characters."""
    with pytest.raises(ValueError, match="Invalid chars in cron"):
        ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER, schedule_cron="0 0 * * * @invalid")


def test_indexing_config_property():
    """Test indexing_config property parsing."""
    connector = ConnectorCreate(
        name="Test",
        connector_type=ConnectorType.LOCAL_FOLDER,
        configuration={"indexing_config": {"use_smart_extraction": True, "extraction_model": "gemini-pro"}},
    )

    indexing_config = connector.indexing_config
    assert isinstance(indexing_config, IndexingConfig)
    assert indexing_config.use_smart_extraction is True
    assert indexing_config.extraction_model == "gemini-pro"


def test_indexing_config_defaults():
    """Test indexing_config with defaults when not in configuration."""
    connector = ConnectorCreate(name="Test", connector_type=ConnectorType.LOCAL_FOLDER)

    indexing_config = connector.indexing_config
    assert indexing_config.use_smart_extraction is False
    assert indexing_config.extraction_model == "gemini-flash"


def test_connector_update_partial():
    """Test partial updates with ConnectorUpdate."""
    update = ConnectorUpdate(name="Updated Name")
    assert update.name == "Updated Name"
    assert update.connector_type is None
    assert update.configuration is None


def test_connector_update_cron_validation():
    """Test cron validation in ConnectorUpdate."""
    with pytest.raises(ValueError, match="expected 5 or 6 fields"):
        ConnectorUpdate(schedule_cron="invalid")


def test_connector_response_structure():
    """Test ConnectorResponse has all required fields."""
    # This would typically come from the database
    response = ConnectorResponse(
        id=uuid4(), name="Test", connector_type=ConnectorType.SQL, status=ConnectorStatus.IDLE, configuration={}
    )
    assert response.id is not None
    assert response.status == ConnectorStatus.IDLE
    assert response.total_docs_count == 0
    assert response.indexed_docs_count == 0
    assert response.failed_docs_count == 0
