"""
Tests to verify the refactoring of Connector models and schemas.
Ensures separation of concerns: Schemas (Pydantic) vs Models (SQLAlchemy/SQLModel).
"""

import pytest
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

from app.schemas.enums import ConnectorType, ScheduleType
from app.schemas.connector import ConnectorBase
from app.models.connector import Connector


def test_schema_is_pure_pydantic():
    """
    Ensure ConnectorBase schema does NOT have sa_column definitions.
    This confirms we successfully decoupled API validation from DB logic.
    """
    # Check fields in the Schema
    fields = ConnectorBase.model_fields

    # Check 'connector_type'
    ctype = fields.get("connector_type")
    assert ctype is not None
    # In Pydantic V2, we check if json_schema_extra or other metadata contains sa_column
    # But usually sa_column is passed to Field() and stored in field_info
    # We want to ensure it is NOT there or is None
    if hasattr(ctype, "sa_column"):
        assert ctype.sa_column is None, "Schema should not have sa_column on connector_type"

    # Check 'configuration'
    config = fields.get("configuration")
    assert config is not None
    if hasattr(config, "sa_column"):
        assert config.sa_column is None, "Schema should not have sa_column on configuration"


def test_model_has_db_columns():
    """
    Ensure Connector Model HAS sa_column definitions.
    This confirms the DB mapping is still present where it belongs.
    """
    # Check fields in the Model
    fields = Connector.model_fields

    # Check 'connector_type'
    ctype = fields.get("connector_type")
    assert ctype is not None
    # SQLModel stores sa_column in the FieldInfo
    # We verify it exists and is a Column
    assert hasattr(ctype, "sa_column"), "Model must have sa_column on connector_type"
    assert isinstance(ctype.sa_column, Column), "connector_type.sa_column must be a SQLAlchemy Column"

    # Check 'configuration'
    config = fields.get("configuration")
    assert config is not None
    assert hasattr(config, "sa_column"), "Model must have sa_column on configuration"
    assert isinstance(config.sa_column, Column), "configuration.sa_column must be a SQLAlchemy Column"
    # Verify type is (or behaves like) JSONB
    # Note: strict type check difficult if generic JSON used, but here we imported JSONB
    assert (
        isinstance(config.sa_column.type, JSONB) or config.sa_column.type.__class__.__name__ == "JSONB"
    ), "configuration column must be JSONB"


def test_model_instantiation():
    """Ensure we can instantiate the model (basic sanity check)."""
    from app.schemas.enums import ConnectorType, ScheduleType

    c = Connector(
        name="Test",
        connector_type=ConnectorType.LOCAL_FILE,
        configuration={"path": "/tmp"},
        schedule_type=ScheduleType.MANUAL,
    )
    assert c.name == "Test"
    assert c.connector_type == ConnectorType.LOCAL_FILE
    assert c.configuration == {"path": "/tmp"}
    # Check defaults
    assert c.chunk_size == 300
