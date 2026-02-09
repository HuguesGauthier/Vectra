"""
Tests for Setting model.
"""

import pytest

from app.models.setting import Setting
from app.schemas.setting import (ALLOWED_SETTING_GROUPS, MAX_KEY_LENGTH,
                                 MAX_VALUE_LENGTH, SettingCreate,
                                 SettingUpdate)


class TestSettingModel:
    """Test setting model."""

    def test_valid_setting_creation(self):
        """Valid setting should be created."""
        setting = Setting(key="app_name", value="Vectra", group="general", is_secret=False)

        assert setting.key == "app_name"
        assert setting.value == "Vectra"
        assert setting.group == "general"
        assert setting.is_secret is False

    def test_secret_setting_creation(self):
        """Secret settings should be flagged."""
        setting = Setting(key="api_key", value="sk_test_123", group="ai", is_secret=True)

        assert setting.is_secret is True
        # Note: value is NOT encrypted automatically
        assert "sk_test_123" in setting.value

    def test_default_is_secret_is_false(self):
        """Settings should not be secret by default."""
        setting = Setting(key="test_key", value="test_value", group="general")
        assert setting.is_secret is False

    def test_all_allowed_groups(self):
        """All allowed setting groups should work."""
        for group in ALLOWED_SETTING_GROUPS:
            setting = Setting(key=f"test_{group}", value="test", group=group)
            assert setting.group == group

    def test_setting_with_description(self):
        """Settings can have descriptions."""
        setting = Setting(
            key="max_upload", value="104857600", group="system", description="Maximum upload size in bytes"
        )
        assert setting.description is not None
        assert "Maximum" in setting.description


class TestSettingCreate:
    """Test SettingCreate schema."""

    def test_setting_create_with_all_fields(self):
        """SettingCreate should accept all fields."""
        create = SettingCreate(
            key="max_upload_size",
            value="104857600",
            group="system",
            is_secret=False,
            description="Maximum file upload size in bytes",
        )

        assert create.key == "max_upload_size"
        assert create.value == "104857600"
        assert create.description is not None

    def test_setting_create_defaults(self):
        """SettingCreate should have proper defaults."""
        create = SettingCreate(key="test", value="value", group="general")
        assert create.is_secret is False
        assert create.description is None


class TestSettingUpdate:
    """Test SettingUpdate schema."""

    def test_partial_update(self):
        """SettingUpdate should allow partial updates."""
        update = SettingUpdate(key="test_key", value="new_value")
        assert update.value == "new_value"
        assert update.description is None

    def test_update_both_fields(self):
        """SettingUpdate can update both fields."""
        update = SettingUpdate(key="test_key", value="updated_value", description="Updated description")
        assert update.value == "updated_value"
        assert update.description == "Updated description"
