import contextlib
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional, Set

# --- 1. Correlation ID Management ---
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="SYSTEM")


def get_correlation_id() -> str:
    """Retrieve the current correlation ID from context."""
    return correlation_id_ctx.get()


def set_correlation_id(c_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_ctx.set(c_id)


@contextlib.contextmanager
def log_context(correlation_id: str):
    """
    Context manager to set and reset correlation ID.
    Prevents context leakage between requests/tasks.
    """
    token = correlation_id_ctx.set(correlation_id)
    try:
        yield
    finally:
        correlation_id_ctx.reset(token)


def generate_request_id() -> str:
    """Generate a unique UUID4 for request tracking."""
    return str(uuid.uuid4())


# --- 2. Sensitive Data Masking ---
# Expanded sensitive keys list
SENSITIVE_KEYS: Set[str] = {
    "api_key",
    "password",
    "secret",
    "token",
    "authorization",
    "key",
    "access_token",
    "refresh_token",
    "client_secret",
    "credit_card",
    "cvv",
}


def mask_sensitive_data(data: Any) -> Any:
    """
    Recursively masks sensitive keys in a dictionary or list.
    Performance optimized: Accesses set O(1).
    """
    if isinstance(data, dict):
        return {
            k: ("[MASKED]" if isinstance(k, str) and k.lower() in SENSITIVE_KEYS else mask_sensitive_data(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data


# --- 3. Structured Logging (JSON) ---
class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for machine parsing (Splunk, Datadog, ELK).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "module": record.module,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for local development.
    Avoids mutating the original record (P1 Fix).
    """

    def format(self, record: logging.LogRecord) -> str:
        # P1 FIX: Don't mutate 'record' directly as it affects other handlers
        # We use standard interpolation by ensuring 'correlation_id' is in the format dict
        record_dict = record.__dict__.copy()
        if "correlation_id" not in record_dict:
            record_dict["correlation_id"] = get_correlation_id()

        # We must temporarily override 'record' attributes for super().format()
        # or just do the formatting manually. Pragmatic: manual format or record copy.
        # super().format relies on the record object, so we use a minimalist approach:
        has_orig = hasattr(record, "correlation_id")
        orig_val = getattr(record, "correlation_id", None)

        if not has_orig:
            record.correlation_id = record_dict["correlation_id"]

        try:
            return super().format(record)
        finally:
            if not has_orig:
                delattr(record, "correlation_id")
            else:
                setattr(record, "correlation_id", orig_val)


# --- 4. Configuration ---
def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Nuclear Configuration of the root logger.
    - Clears all existing handlers from all loggers.
    - Configures root logger with a StreamHandler (stderr).
    - Sets explicit levels for root and handler.
    """
    # 1. Clear ALL existing handlers
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
        logging.getLogger(name).disabled = False

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(level)

    # 2. Handler setup
    # Use stdout instead of stderr to align with print() behavior and avoid terminal separation issues
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if json_format:
        formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    else:
        log_format = "[%(correlation_id)s] %(asctime)s | %(levelname)s | %(name)s | %(message)s"
        formatter = ConsoleFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)

    # Add to Root
    root_logger.addHandler(handler)

    # 3. Suppress noisy libraries
    for noisy in ["uvicorn.access", "multipart", "httpx", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # 4. Filter out annoying Pydantic pickling warnings
    class UnpickleableAttributeFilter(logging.Filter):
        def filter(self, record):
            return "Removing unpickleable private attribute" not in record.getMessage()

    handler.addFilter(UnpickleableAttributeFilter())

    # Startup message
    print(f"DEBUG: Logging initialized at level {level} (stdout enforced)", file=sys.stdout)
