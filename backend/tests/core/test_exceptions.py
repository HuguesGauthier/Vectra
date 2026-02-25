import pytest

from app.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DuplicateError,
    ExternalDependencyError,
    EntityNotFound,
    FileSystemError,
    FunctionalError,
    InvalidStateError,
    RateLimitError,
    TechnicalError,
    ValidationError,
    VectraException,
)


class TestVectraException:
    """Test base exception behavior."""

    def test_base_exception_structure(self):
        """Should set default attributes correctly."""
        # VectraException is abstract but we can test subclasses or mock
        # Testing a concrete subclass is easier
        exc = FunctionalError("Something wrong", "FUNC_ERR")
        assert exc.message == "Something wrong"
        assert exc.error_code == "FUNC_ERR"
        assert exc.status_code == 400
        assert exc.details == {}

    def test_mutable_defaults_safety(self):
        """Should not share details dictionary between instances."""
        exc1 = FunctionalError("Error 1", "E1", details={"key": "val1"})
        exc2 = FunctionalError("Error 2", "E2")

        assert exc1.details == {"key": "val1"}
        assert exc2.details == {}

        # Modify one, check other
        exc1.details["new"] = "val"
        assert "new" not in exc2.details

    def test_str_representation(self):
        """Should provide rich string representation."""
        exc = TechnicalError("System Fail", "SYS_ERR", details={"cpu": "99%"})
        s = str(exc)
        assert "[TECHNICAL]" in s
        assert "SYS_ERR" in s
        assert "System Fail" in s
        assert "cpu" in s

    def test_to_dict_serialization(self):
        """Should serialize to dictionary for API responses."""
        exc = EntityNotFound(entity_type="User", entity_id="123")
        data = exc.to_dict()

        assert data["type"] == "FUNCTIONAL"
        assert data["error_code"] == "entity_not_found"
        assert data["status_code"] == 404
        assert data["details"]["entity_type"] == "User"
        assert data["details"]["entity_id"] == "123"


class TestSpecificExceptions:
    """Test specific exception helpers."""

    def test_configuration_error(self):
        """ConfigurationError should have correct status and defaults."""
        exc = ConfigurationError("Missing key", config_key="SECRET_KEY")
        assert exc.status_code == 500
        assert exc.details["config_key"] == "SECRET_KEY"
        assert exc.type == "TECHNICAL"

    def test_entity_not_found(self):
        """EntityNotFound should be 404."""
        exc = EntityNotFound()
        assert exc.status_code == 404
        assert exc.type == "FUNCTIONAL"

    def test_authentication_error(self):
        """AuthenticationError should be 401."""
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "authentication_failed"
        assert exc.type == "FUNCTIONAL"

    def test_rate_limit_error(self):
        """RateLimitError should be 429 and include retry_after."""
        exc = RateLimitError(retry_after=60)
        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60
        assert exc.error_code == "rate_limit_exceeded"

    def test_validation_error(self):
        """ValidationError should be 422."""
        exc = ValidationError(field="email")
        assert exc.status_code == 422
        assert exc.details["field"] == "email"

    def test_invalid_state_error(self):
        """InvalidStateError should be 422."""
        exc = InvalidStateError(current_state="published")
        assert exc.status_code == 422
        assert exc.details["current_state"] == "published"

    def test_duplicate_error(self):
        """DuplicateError should be 409."""
        exc = DuplicateError()
        assert exc.status_code == 409

    def test_external_dependency_error(self):
        """ExternalDependencyError should be 503."""
        exc = ExternalDependencyError(service="OpenAI")
        assert exc.status_code == 503
        assert exc.details["failed_service"] == "OpenAI"

    def test_filesystem_error(self):
        """FileSystemError should be 500."""
        exc = FileSystemError(file_path="/tmp/test.txt")
        assert exc.status_code == 500
        assert exc.details["file_path"] == "/tmp/test.txt"
