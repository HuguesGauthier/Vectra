"""
Tests for app.core.settings module.

Validates:
- Settings loading and validation
- Environment-specific validation (dev/test/production)
- Secret strength validation
- Provider configuration validation
- Error handling
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.settings import Settings, get_settings


class TestSettingsBasics:
    """Test basic settings loading and defaults."""

    def test_settings_loads_with_defaults(self):
        """Settings should load successfully with default values in development."""
        with patch.dict(os.environ, {"ENV": "development", "GEMINI_API_KEY": "dummy"}, clear=True):
            settings = Settings()

            assert settings.ENV == "development"
            import sys

            expected_host = "127.0.0.1" if sys.platform == "win32" else "localhost"
            assert settings.DATABASE_URL == f"postgresql+asyncpg://vectra:vectra@{expected_host}:5432/vectra"
            assert settings.DB_POOL_SIZE == 20
            # Ephemeral secret check
            assert len(settings.SECRET_KEY) == 64
            assert settings.DEBUG is False
            assert settings.EMBEDDING_PROVIDER == "gemini"

    def test_settings_from_environment_variables(self):
        """Settings should override defaults with environment variables."""
        with patch.dict(
            os.environ,
            {
                "ENV": "test",
                "DATABASE_URL": "postgresql+asyncpg://custom:custom@testhost:5432/testdb",
                "DB_POOL_SIZE": "50",
                "LOG_LEVEL": "DEBUG",
                "GEMINI_API_KEY": "test-gemini-key",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.ENV == "test"
            assert settings.DATABASE_URL == "postgresql+asyncpg://custom:custom@testhost:5432/testdb"
            assert settings.DB_POOL_SIZE == 50
            assert settings.LOG_LEVEL == "DEBUG"
            assert settings.GEMINI_API_KEY == "test-gemini-key"


class TestSecretValidation:
    """Test secret key strength validation."""

    def test_weak_secret_allowed_in_development(self):
        """Weak secrets should be allowed in development mode with warning."""
        with patch.dict(os.environ, {"ENV": "development"}, clear=True):
            settings = Settings(SECRET_KEY="dev-secret-key-replace-in-production", WORKER_SECRET="dev-worker-secret")

            # Should not raise, just warn
            assert settings.SECRET_KEY == "dev-secret-key-replace-in-production"

    def test_weak_secret_rejected_in_production(self):
        """Weak secrets should raise ValueError in production."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "prod-key"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    ENV="production",
                    SECRET_KEY="dev-secret-key-replace-in-production",
                    WORKER_SECRET="strong-enough-secret-for-production-testing-purposes-12345",
                    FIRST_SUPERUSER_PASSWORD="strong-pass-123!",
                )

            assert "weak/default patterns" in str(exc_info.value)

    def test_short_secret_rejected_in_production(self):
        """Secrets shorter than 32 chars should be rejected in production."""
        with patch.dict(os.environ, {"ENV": "production", "GEMINI_API_KEY": "prod-key"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(SECRET_KEY="short", WORKER_SECRET="also-short", FIRST_SUPERUSER_PASSWORD="strong-pass-123!")

            assert "at least 32 characters" in str(exc_info.value)

    def test_strong_secret_accepted_in_production(self):
        """Strong secrets should be accepted in production."""
        with patch.dict(
            os.environ, {"ENV": "production", "GEMINI_API_KEY": "strong-gemini-key-for-production-testing"}, clear=True
        ):
            settings = Settings(
                SECRET_KEY="a" * 64,  # Strong secret
                WORKER_SECRET="b" * 64,
                FIRST_SUPERUSER_PASSWORD="super-strong-admin-password-123!",
            )

            assert len(settings.SECRET_KEY) == 64
            assert len(settings.WORKER_SECRET) == 64


class TestProviderValidation:
    """Test embedding provider and API key validation."""

    def test_gemini_provider_without_key_fails_in_development(self):
        """Selecting Gemini without API key should fail in development."""
        with patch.dict(os.environ, {"ENV": "development"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(EMBEDDING_PROVIDER="gemini", GEMINI_API_KEY=None)

            assert "requires GEMINI_API_KEY" in str(exc_info.value)

    def test_openai_provider_without_key_fails(self):
        """Selecting OpenAI without API key should fail."""
        with patch.dict(os.environ, {"ENV": "development"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY=None)

            assert "requires OPENAI_API_KEY" in str(exc_info.value)

    def test_gemini_provider_with_key_succeeds(self):
        """Gemini provider with API key should work."""
        with patch.dict(os.environ, {"ENV": "development"}, clear=True):
            settings = Settings(EMBEDDING_PROVIDER="gemini", GEMINI_API_KEY="test-gemini-key")

            assert settings.EMBEDDING_PROVIDER == "gemini"
            assert settings.GEMINI_API_KEY == "test-gemini-key"

    def test_local_provider_no_key_needed(self):
        """Local provider should not require API keys."""
        with patch.dict(os.environ, {"ENV": "development"}, clear=True):
            settings = Settings(EMBEDDING_PROVIDER="local", GEMINI_API_KEY=None, OPENAI_API_KEY=None)

            assert settings.EMBEDDING_PROVIDER == "local"

    def test_provider_validation_skipped_in_test_env(self):
        """API key validation should be skipped in test environment."""
        with patch.dict(os.environ, {"ENV": "test"}, clear=True):
            # Should not raise even without API keys
            settings = Settings(EMBEDDING_PROVIDER="gemini", GEMINI_API_KEY=None)

            assert settings.ENV == "test"


class TestProductionValidation:
    """Test production-specific validation rules."""

    def test_debug_true_rejected_in_production(self):
        """DEBUG=True should be rejected in production."""
        with patch.dict(os.environ, {"ENV": "production", "GEMINI_API_KEY": "prod-key"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    DEBUG=True, SECRET_KEY="a" * 64, WORKER_SECRET="b" * 64, FIRST_SUPERUSER_PASSWORD="strong-pass-123"
                )

            assert "DEBUG must be False in production" in str(exc_info.value)

    def test_default_admin_password_rejected_in_production(self):
        """Default admin password should be rejected in production."""
        with patch.dict(os.environ, {"ENV": "production", "GEMINI_API_KEY": "prod-key"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(SECRET_KEY="a" * 64, WORKER_SECRET="b" * 64, FIRST_SUPERUSER_PASSWORD="vectra123!")

            assert "Default FIRST_SUPERUSER_PASSWORD" in str(exc_info.value)

    def test_production_with_secure_settings_succeeds(self):
        """Production should work with all secure settings."""
        with patch.dict(
            os.environ, {"ENV": "production", "GEMINI_API_KEY": "production-gemini-api-key-for-testing"}, clear=True
        ):
            settings = Settings(
                DEBUG=False,
                SECRET_KEY="a" * 64,
                WORKER_SECRET="b" * 64,
                FIRST_SUPERUSER_PASSWORD="secure-admin-password-456!",
            )

            assert settings.ENV == "production"
            assert settings.DEBUG is False


class TestLazyInitialization:
    """Test lazy initialization pattern."""

    def test_get_settings_returns_singleton(self):
        """get_settings() should return the same instance."""
        with patch.dict(os.environ, {"ENV": "test"}, clear=True):
            # Clear the global singleton
            from app.core import settings

            settings._settings = None

            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

    def test_get_settings_error_handling(self):
        """get_settings should handle ValidationError properly."""
        with patch.dict(os.environ, {"ENV": "test"}, clear=True):
            # Clear singleton
            from app.core import settings

            settings._settings = None

            # Mock Settings to raise ValidationError
            with patch("app.core.settings.Settings") as MockSettings:
                MockSettings.side_effect = ValidationError.from_exception_data(
                    "test", [{"type": "missing", "loc": ("SECRET_KEY",), "msg": "field required", "input": {}}]
                )

                with pytest.raises(ValidationError):
                    get_settings()


class TestEnvironmentDetection:
    """Test environment-based behavior."""

    def test_development_environment(self):
        """Development environment should have relaxed validation."""
        with patch.dict(os.environ, {"ENV": "development"}, clear=True):
            settings = Settings()

            assert settings.ENV == "development"
            # Ephemeral secret generated in dev
            assert len(settings.SECRET_KEY) == 64
            assert len(settings.WORKER_SECRET) > 0

    def test_test_environment(self):
        """Test environment should skip API key validation."""
        with patch.dict(os.environ, {"ENV": "test"}, clear=True):
            settings = Settings(EMBEDDING_PROVIDER="gemini", GEMINI_API_KEY=None)  # Allowed in test

            assert settings.ENV == "test"

    def test_production_environment_strict_validation(self):
        """Production should enforce strict validation."""
        with patch.dict(os.environ, {"ENV": "production", "GEMINI_API_KEY": "prod-api-key"}, clear=True):
            # Must provide strong secrets and proper config
            settings = Settings(
                SECRET_KEY="a" * 64,
                WORKER_SECRET="b" * 64,
                DEBUG=False,
                FIRST_SUPERUSER_PASSWORD="strong-password-123!",
            )

            assert settings.ENV == "production"


class TestGetSettingsThreadSafety:
    """Test thread-safety of the get_settings() singleton."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton before each test."""
        # Need to import inside to affect the module state
        from app.core import settings as settings_module

        old_val = settings_module._settings
        settings_module._settings = None
        yield
        settings_module._settings = old_val

    def test_get_settings_returns_same_instance(self):
        """Multiple calls should return the same Settings instance."""
        with patch.dict(os.environ, {"ENV": "test", "GEMINI_API_KEY": "test-key"}, clear=True):
            s1 = get_settings()
            s2 = get_settings()
            assert s1 is s2

    def test_get_settings_thread_safety(self):
        """Concurrent calls should result in only one Settings instance."""
        import threading

        with patch.dict(os.environ, {"ENV": "test", "GEMINI_API_KEY": "test-key"}, clear=True):
            results = []

            def get_and_store():
                s = get_settings()
                results.append(id(s))

            # Spawn 10 threads
            threads = [threading.Thread(target=get_and_store) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All threads should have gotten the same object (same id)
            assert len(set(results)) == 1


class TestDatabaseURLValidation:
    """Test DATABASE_URL environment-specific handling."""

    def test_windows_localhost_replacement(self):
        """On Windows, localhost should be replaced with 127.0.0.1."""
        import sys

        if sys.platform != "win32":
            pytest.skip("Only relevant on Windows")

        with patch.dict(
            os.environ,
            {
                "ENV": "test",
                "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
                "GEMINI_API_KEY": "test-key",
            },
            clear=True,
        ):
            settings = Settings()
            assert "127.0.0.1" in settings.DATABASE_URL
            assert "localhost" not in settings.DATABASE_URL
