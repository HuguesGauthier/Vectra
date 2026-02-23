"""
Tests for Setting model.
"""

import pytest
from pydantic import ValidationError

from app.models.setting import Setting
from app.models.enums import SettingGroup


class TestSettingModel:
    """Test setting model."""

    def test_valid_setting_creation(self):
        """Valid setting should be created."""
        setting = Setting(key="app_name", value="Vectra", group=SettingGroup.GENERAL, is_secret=False)

        assert setting.key == "app_name"
        assert setting.value == "Vectra"
        assert setting.group == SettingGroup.GENERAL
        assert setting.is_secret is False

    def test_secret_setting_creation(self):
        """Secret settings should be flagged."""
        setting = Setting(key="api_key", value="sk_test_123", group=SettingGroup.AI, is_secret=True)
        assert setting.is_secret is True

    def test_all_setting_groups(self):
        """All allowed setting groups should work."""
        for group in SettingGroup:
            setting = Setting(key=f"test_{group}", value="test", group=group)
            assert setting.group == group

    def test_setting_with_description(self):
        """Settings can have descriptions."""
        setting = Setting(
            key="max_upload", value="104857600", group=SettingGroup.SYSTEM, description="Maximum upload size"
        )
        assert setting.description == "Maximum upload size"

    def test_validation_on_assignment(self):
        """Validation should trigger on attribute assignment (Robustness P1)."""
        setting = Setting(key="test", value="val", group=SettingGroup.GENERAL)

        # This should trigger Pydantic validation because of validate_assignment=True
        with pytest.raises(ValidationError):
            setting.group = "invalid_group"  # type: ignore
