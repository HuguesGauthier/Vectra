import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from app.core.logging import (JSONFormatter, get_correlation_id,
                              mask_sensitive_data, set_correlation_id,
                              setup_logging)


class TestCorrelationID:
    """Test correlation ID context management."""

    def test_get_set_correlation_id(self):
        """Should retrieve what was set."""
        set_correlation_id("test-id-123")
        assert get_correlation_id() == "test-id-123"

        set_correlation_id("test-id-456")
        assert get_correlation_id() == "test-id-456"


class TestDataMasking:
    """Test sensitive data redaction."""

    def test_mask_sensitive_keys(self):
        """Should mask keys in SENSITIVE_KEYS set."""
        data = {
            "password": "secret_pass",
            "safe": "value",
            "nested": {"token": "secret_token", "api_key": "secret_key"},
        }
        masked = mask_sensitive_data(data)

        assert masked["password"] == "[MASKED]"
        assert masked["safe"] == "value"
        assert masked["nested"]["token"] == "[MASKED]"
        assert masked["nested"]["api_key"] == "[MASKED]"

    def test_mask_in_list(self):
        """Should mask sensitive data inside lists."""
        data = [{"password": "123"}, {"safe": "456"}]
        masked = mask_sensitive_data(data)
        assert masked[0]["password"] == "[MASKED]"
        assert masked[1]["safe"] == "456"


class TestJSONFormatter:
    """Test structured logging output."""

    def test_json_format_structure(self):
        """Should produce valid JSON with required fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_path.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "corr-123"

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["level"] == "INFO"
        assert log_dict["message"] == "Test message"
        assert log_dict["correlation_id"] == "corr-123"
        assert log_dict["logger"] == "test_logger"


class TestSetupLogging:
    """Test logger configuration."""

    def test_setup_logging_idempotency(self):
        """Should replace handlers rather than duplicate."""
        setup_logging(json_format=True)
        root = logging.getLogger()
        handlers_count = len(root.handlers)

        setup_logging(json_format=True)
        assert len(root.handlers) == handlers_count  # Should stay same, usually 1
