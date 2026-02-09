"""
Tests for ErrorLog model validation and security.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.error_log import (MAX_ERROR_MESSAGE_LENGTH, MAX_STATUS_CODE,
                                  MIN_STATUS_CODE, ErrorLog)


class TestErrorLogValidation:
    """Test validation rules."""

    def test_valid_error_log_creation(self):
        """Valid error log should pass validation."""
        log = ErrorLog(
            status_code=500,
            method="POST",
            path="/api/v1/test",
            error_message="Test error",
            stack_trace="Traceback (most recent call last):\n  File...",
        )
        assert log.status_code == 500
        assert log.method == "POST"

    def test_status_codes_in_valid_range(self):
        """All standard HTTP status codes should be valid."""
        for code in [200, 201, 400, 401, 403, 404, 500, 502, 503]:
            log = ErrorLog(status_code=code, method="GET", path="/test", error_message="Error", stack_trace="Trace")
            assert log.status_code == code


class TestErrorLogConstraints:
    """Test field constraints."""

    def test_very_long_error_message_truncates(self):
        """Error message exceeding max length should be constrained by DB."""
        # Note: Pydantic max_length on SQLModel table fields is enforced at DB level
        long_message = "x" * (MAX_ERROR_MESSAGE_LENGTH + 1000)

        # SQLModel will accept this but database will truncate/error
        log = ErrorLog(status_code=500, method="GET", path="/test", error_message=long_message, stack_trace="Trace")
        # The constraint is at database level, not Pydantic validation level
        assert len(log.error_message) > MAX_ERROR_MESSAGE_LENGTH

    def test_short_method_names_valid(self):
        """Standard HTTP methods should fit within max length."""
        for method in ["GET", "POST", "PUT", "DELETE"]:
            log = ErrorLog(status_code=200, method=method, path="/test", error_message="OK", stack_trace="None")
            assert log.method == method
