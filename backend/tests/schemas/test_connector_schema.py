"""
Tests for Connector Schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.connector import ConnectorCreate, ConnectorUpdate


def test_connector_validation_type():
    with pytest.raises(ValidationError) as exc:
        ConnectorCreate(name="Fail", connector_type="invalid")
    assert "Invalid type" in str(exc.value)


def test_connector_validation_cron():
    with pytest.raises(ValidationError) as exc:
        ConnectorCreate(name="Fail", connector_type="s3", schedule_cron="invalid cron")
    assert "Invalid cron" in str(exc.value)

    # Valid cron
    c = ConnectorCreate(name="OK", connector_type="s3", schedule_cron="*/5 * * * *")
    assert c.schedule_cron == "*/5 * * * *"


def test_connector_config_size():
    big_dict = {"data": "a" * 100001}
    with pytest.raises(ValidationError) as exc:
        ConnectorCreate(name="Fail", connector_type="s3", configuration=big_dict)
    assert "too large" in str(exc.value)


def test_connector_update_partial():
    u = ConnectorUpdate(schedule_type="cron")
    assert u.name is None
    assert u.schedule_type == "cron"
