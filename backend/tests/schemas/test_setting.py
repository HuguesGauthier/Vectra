"""
Unit tests for backend/app/schemas/setting.py
Tests cover validation, DoS protection, group validation, and secret handling.
"""

import pytest
from datetime import datetime

from pydantic import ValidationError

from app.schemas.setting import (
    ALLOWED_SETTING_GROUPS,
    MAX_DESCRIPTION_LENGTH,
    MAX_GROUP_LENGTH,
    MAX_KEY_LENGTH,
    MAX_VALUE_LENGTH,
    SettingBase,
    SettingCreate,
    SettingResponse,
    SettingUpdate,
)


class TestSettingBase:
    """Test SettingBase schema."""

    def test_valid_setting_base(self):
        """Test creating a valid setting."""
        setting = SettingBase(
            key="api_key",
            value="test_value",
            group="general",
            is_secret=False,
            description="Test setting",
        )
        assert setting.key == "api_key"
        assert setting.value == "test_value"
        assert setting.group == "general"
        assert setting.is_secret is False
        assert setting.description == "Test setting"

    def test_default_is_secret(self):
        """Test that is_secret defaults to False."""
        setting = SettingBase(key="test", value="value", group="general")
        assert setting.is_secret is False

    def test_optional_description(self):
        """Test that description is optional."""
        setting = SettingBase(key="test", value="value", group="general")
        assert setting.description is None


class TestGroupValidation:
    """Test group validation."""

    def test_all_allowed_groups_valid(self):
        """Test that all allowed groups are accepted."""
        from app.models.enums import SettingGroup

        for group in SettingGroup:
            setting = SettingBase(key="test", value="value", group=group)
            assert setting.group == group

    def test_invalid_group_rejected(self):
        """Test that invalid groups are rejected (Pydantic Enum validation)."""
        with pytest.raises(ValidationError):
            SettingBase(key="test", value="value", group="invalid_group")  # type: ignore

    def test_group_validation_error_message(self):
        """Test that validation error contains relevant info."""
        with pytest.raises(ValidationError) as exc_info:
            SettingBase(key="test", value="value", group="hacker_group")  # type: ignore

        error_msg = str(exc_info.value).lower()
        # Pydantic V2 enum error contains 'input should be' or mentions the enum
        assert "should be" in error_msg or "settinggroup" in error_msg


class TestDoSProtection:
    """Test DoS protection via length limits."""

    def test_empty_key_rejected(self):
        """Test that empty keys are rejected."""
        with pytest.raises(ValidationError):
            SettingBase(key="", value="value", group="general")

    def test_max_key_length_enforced(self):
        """Test that keys exceeding MAX_KEY_LENGTH are rejected."""
        long_key = "x" * (MAX_KEY_LENGTH + 1)
        with pytest.raises(ValidationError):
            SettingBase(key=long_key, value="value", group="general")

    def test_max_key_length_boundary(self):
        """Test that keys at exactly MAX_KEY_LENGTH are accepted."""
        max_key = "x" * MAX_KEY_LENGTH
        setting = SettingBase(key=max_key, value="value", group="general")
        assert len(setting.key) == MAX_KEY_LENGTH

    def test_max_value_length_enforced(self):
        """Test that values exceeding MAX_VALUE_LENGTH are rejected (DoS protection)."""
        long_value = "x" * (MAX_VALUE_LENGTH + 1)
        with pytest.raises(ValidationError):
            SettingBase(key="test", value=long_value, group="general")

    def test_max_value_length_boundary(self):
        """Test that values at exactly MAX_VALUE_LENGTH are accepted."""
        max_value = "x" * MAX_VALUE_LENGTH
        setting = SettingBase(key="test", value=max_value, group="general")
        assert len(setting.value) == MAX_VALUE_LENGTH

    def test_max_group_length_enforced(self):
        """Test that groups exceeding MAX_GROUP_LENGTH are rejected."""
        long_group = "x" * (MAX_GROUP_LENGTH + 1)
        with pytest.raises(ValidationError):
            SettingBase(key="test", value="value", group=long_group)

    def test_max_description_length_enforced(self):
        """Test that descriptions exceeding MAX_DESCRIPTION_LENGTH are rejected."""
        long_description = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError):
            SettingBase(
                key="test",
                value="value",
                group="general",
                description=long_description,
            )

    def test_max_description_length_boundary(self):
        """Test that descriptions at exactly MAX_DESCRIPTION_LENGTH are accepted."""
        max_description = "x" * MAX_DESCRIPTION_LENGTH
        setting = SettingBase(
            key="test",
            value="value",
            group="general",
            description=max_description,
        )
        assert len(setting.description) == MAX_DESCRIPTION_LENGTH


class TestSettingCreate:
    """Test SettingCreate schema."""

    def test_valid_setting_create(self):
        """Test creating a valid setting creation request."""
        setting = SettingCreate(
            key="openai_api_key",
            value="sk-test123",
            group="ai",
            is_secret=True,
            description="OpenAI API Key",
        )
        assert setting.key == "openai_api_key"
        assert setting.value == "sk-test123"
        assert setting.group == "ai"
        assert setting.is_secret is True
        assert setting.description == "OpenAI API Key"

    def test_create_inherits_validation(self):
        """Test that SettingCreate inherits validation from SettingBase."""
        with pytest.raises(ValidationError):
            SettingCreate(key="test", value="value", group="invalid_group")


class TestSettingUpdate:
    """Test SettingUpdate schema (partial updates)."""

    def test_valid_setting_update(self):
        """Test updating a setting."""
        update = SettingUpdate(key="test", value="new_value")
        assert update.key == "test"
        assert update.value == "new_value"
        assert update.group is None
        assert update.is_secret is None

    def test_update_group_valid(self):
        """Test updating group to a valid value."""
        update = SettingUpdate(key="test", group="ai")
        assert update.group == "ai"

    def test_update_group_invalid(self):
        """Test that invalid groups are rejected in updates."""
        with pytest.raises(ValidationError) as exc_info:
            SettingUpdate(key="test", group="invalid_group")  # type: ignore

        error_msg = str(exc_info.value).lower()
        assert "should be" in error_msg or "settinggroup" in error_msg

    def test_update_group_none_valid(self):
        """Test that None group is valid (no update)."""
        update = SettingUpdate(key="test", value="value", group=None)
        assert update.group is None

    def test_update_is_secret(self):
        """Test updating is_secret flag."""
        update = SettingUpdate(key="test", is_secret=True)
        assert update.is_secret is True

    def test_update_description(self):
        """Test updating description."""
        update = SettingUpdate(key="test", description="New description")
        assert update.description == "New description"

    def test_key_required_in_update(self):
        """Test that key is required even in updates."""
        with pytest.raises(ValidationError):
            SettingUpdate(value="test")  # type: ignore


class TestSettingResponse:
    """Test SettingResponse schema."""

    def test_valid_setting_response(self):
        """Test creating a valid setting response."""
        now = datetime.utcnow()
        response = SettingResponse(
            key="test_key",
            value="test_value",
            group="system",
            is_secret=False,
            description="Test setting",
            updated_at=now,
        )
        assert response.key == "test_key"
        assert response.value == "test_value"
        assert response.group == "system"
        assert response.is_secret is False
        assert response.updated_at == now

    def test_updated_at_optional(self):
        """Test that updated_at is optional."""
        response = SettingResponse(key="test", value="value", group="general")
        assert response.updated_at is None


class TestSecretHandling:
    """Test secret setting handling."""

    def test_secret_setting_creation(self):
        """Test creating a secret setting."""
        setting = SettingBase(
            key="database_password",
            value="super_secret_password",
            group="system",
            is_secret=True,
        )
        assert setting.is_secret is True
        assert setting.value == "super_secret_password"

    def test_non_secret_setting_creation(self):
        """Test creating a non-secret setting."""
        setting = SettingBase(key="app_name", value="Vectra", group="general", is_secret=False)
        assert setting.is_secret is False


class TestEdgeCases:
    """Test edge cases and production scenarios."""

    def test_unicode_value(self):
        """Test that Unicode values are handled correctly."""
        setting = SettingBase(
            key="welcome_message",
            value="Welcome 世界 🌍",
            group="general",
        )
        assert setting.value == "Welcome 世界 🌍"

    def test_json_value(self):
        """Test that JSON strings can be stored as values."""
        json_value = '{"key": "value", "nested": {"data": 123}}'
        setting = SettingBase(key="config", value=json_value, group="system")
        assert setting.value == json_value

    def test_empty_value_valid(self):
        """Test that empty values are valid (unlike keys)."""
        setting = SettingBase(key="test", value="", group="general")
        assert setting.value == ""

    def test_serialization_to_dict(self):
        """Test that settings can be serialized to dict (for API responses)."""
        setting = SettingResponse(
            key="test",
            value="value",
            group="general",
            is_secret=False,
            updated_at=datetime.utcnow(),
        )
        data = setting.model_dump()
        assert isinstance(data, dict)
        assert data["key"] == "test"
        assert data["is_secret"] is False


class TestConstants:
    """Test exported constants."""

    def test_allowed_setting_groups_not_empty(self):
        """Test that ALLOWED_SETTING_GROUPS is not empty."""
        assert len(ALLOWED_SETTING_GROUPS) > 0

    def test_allowed_setting_groups_contains_expected(self):
        """Test that ALLOWED_SETTING_GROUPS contains expected groups."""
        expected_groups = {"general", "ai", "system", "auth"}
        assert expected_groups.issubset(ALLOWED_SETTING_GROUPS)

    def test_max_lengths_reasonable(self):
        """Test that max lengths are reasonable for production."""
        assert 10 <= MAX_KEY_LENGTH <= 500
        assert 100 <= MAX_VALUE_LENGTH <= 100000
        assert 10 <= MAX_GROUP_LENGTH <= 200
        assert 50 <= MAX_DESCRIPTION_LENGTH <= 5000
