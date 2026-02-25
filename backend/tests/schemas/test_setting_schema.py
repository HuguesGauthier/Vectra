"""
Tests for Setting Schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.setting import SettingCreate, SettingUpdate


def test_setting_create_valid():
    s = SettingCreate(key="test_key", value="val", group="system", is_secret=True)
    assert s.group == "system"
    assert s.is_secret is True


def test_setting_create_invalid_group():
    with pytest.raises(ValidationError) as exc:
        SettingCreate(key="k", value="v", group="hacker_group")
    assert "Input should be" in str(exc.value)


def test_setting_update_limits():
    # Success
    u = SettingUpdate(key="test", value="new")
    assert u.value == "new"

    # Validation is enforced by field constraints in types usually,
    # but strictly speaking Optional fields need careful validation if constraints are on the Field.
    # Pydantic V2 validates Field constraints even for Optionals if value is provided.

    long_val = "a" * 5001
    with pytest.raises(ValidationError) as exc:
        SettingUpdate(key="test", value=long_val)
    assert "at most 5000 characters" in str(exc.value)
