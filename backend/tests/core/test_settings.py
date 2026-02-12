import os
import sys
import pytest
from pydantic import ValidationError
from app.core.settings import Settings


class TestSettingsCore:
    def test_settings_defaults_development(self):
        """Happy Path: Verify settings load with defaults in development."""
        settings = Settings(ENV="development", DEBUG=False)
        assert settings.ENV == "development"
        assert settings.DEBUG is False
        # SECRET_KEY should be auto-generated for non-prod
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) == 64  # hex(32 bytes)

    def test_production_validation_missing_secrets(self):
        """Worst Case: Verify production fails if secrets are missing."""
        with pytest.raises(ValidationError):
            Settings(ENV="production", SECRET_KEY=None)

    def test_production_validation_default_db(self):
        """Worst Case: Verify production fails if default DATABASE_URL is used."""
        with pytest.raises(ValidationError):
            Settings(
                ENV="production",
                SECRET_KEY="very-long-and-secure-production-secret-key",
                WORKER_SECRET="another-very-secure-worker-secret-key",
                FIRST_SUPERUSER_PASSWORD="strong-password-123",
                GEMINI_API_KEY="test-gemini-key",
                DATABASE_URL="postgresql+asyncpg://vectra:vectra@localhost:5432/vectra",
            )

    def test_windows_db_url_fixer(self, monkeypatch):
        """Happy Path: Verify localhost is replaced with 127.0.0.1 on Windows."""
        monkeypatch.setattr(sys, "platform", "win32")

        # Test DATABASE_URL
        settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
        assert "127.0.0.1" in settings.DATABASE_URL
        assert "localhost" not in settings.DATABASE_URL

    def test_windows_qdrant_host_fixer(self, monkeypatch):
        """Happy Path: Verify QDRANT_HOST 'localhost' is fixed on Windows."""
        monkeypatch.setattr(sys, "platform", "win32")

        settings = Settings(QDRANT_HOST="localhost")
        assert settings.QDRANT_HOST == "127.0.0.1"

    def test_provider_dependency_validation(self):
        """Worst Case: Verify missing API key for provider raises error."""
        # Ensure we don't fail on prod secret checks first
        with pytest.raises(ValidationError, match="requires GEMINI_API_KEY"):
            Settings(
                ENV="development",
                EMBEDDING_PROVIDER="gemini",
                GEMINI_API_KEY=None,
                SECRET_KEY="test-secret",
                WORKER_SECRET="test-worker",
                FIRST_SUPERUSER_PASSWORD="test-password",
            )
