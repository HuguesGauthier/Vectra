from abc import ABC
from typing import Any, Dict, Optional


class VectraException(Exception, ABC):
    """
    Base exception for all application errors.

    ARCHITECT NOTE 1: Abstract Base Class
    Makes it explicit that VectraException should not be instantiated directly.
    All exceptions should derive from Functional or Technical errors.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

        # ARCHITECT NOTE 2: Safe Mutable Default Handling
        # Always create a new dict instead of using shared default
        self.details: Dict[str, Any] = details.copy() if details else {}

        # Will be set by subclasses
        self.type: str = "UNKNOWN"

    def __str__(self) -> str:
        """
        ARCHITECT NOTE 3: Rich String Representation

        Provides context-rich output for logging and debugging.
        Includes error_code and details for better troubleshooting.
        """
        details_str = f", details={self.details}" if self.details else ""
        return f"[{self.type}] {self.error_code}: {self.message}{details_str}"

    def __repr__(self) -> str:
        """Technical representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"status_code={self.status_code}, "
            f"details={self.details!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        ARCHITECT NOTE 4: Serialization Support

        Useful for API responses and structured logging.
        """
        return {
            "type": self.type,
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


class FunctionalError(VectraException):
    """
    Base class for functional (business logic) errors.

    These are errors caused by user actions or business rule violations.
    Typically result in 4xx status codes.
    """

    def __init__(self, message: str, error_code: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, status_code, details)
        self.type = "FUNCTIONAL"


class TechnicalError(VectraException):
    """
    Base class for technical (system) errors.

    These are errors caused by infrastructure, external dependencies,
    or unexpected system behavior. Typically result in 5xx status codes.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "technical_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, status_code, details)
        self.type = "TECHNICAL"


# ============================================================================
# FUNCTIONAL ERRORS (4xx)
# ============================================================================


class EntityNotFound(FunctionalError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Entity not found",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        # ARCHITECT NOTE 5: Structured Details
        # Provide structured fields for common debugging info
        _details = details.copy() if details else {}
        if entity_type:
            _details["entity_type"] = entity_type
        if entity_id:
            _details["entity_id"] = entity_id

        super().__init__(message, error_code="entity_not_found", status_code=404, details=_details)


class DuplicateError(FunctionalError):
    """Raised when attempting to create a duplicate resource."""

    def __init__(self, message: str = "Resource already exists", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="duplicate_resource", status_code=409, details=details)


class ValidationError(FunctionalError):
    """
    ARCHITECT NOTE 6: New Exception for Input Validation

    Raised when request data fails validation (e.g., Pydantic errors).
    Distinct from InvalidStateError which is about business state.
    """

    def __init__(
        self, message: str = "Validation failed", field: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        _details = details.copy() if details else {}
        if field:
            _details["field"] = field

        super().__init__(message, error_code="validation_error", status_code=422, details=_details)


class InvalidStateError(FunctionalError):
    """
    Raised when an action is invalid for the current business state.

    Example: Trying to publish a draft that's already published,
    or deleting a resource that's in use.
    """

    def __init__(
        self,
        message: str = "Invalid operation for current state",
        current_state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details.copy() if details else {}
        if current_state:
            _details["current_state"] = current_state

        super().__init__(message, error_code="invalid_state", status_code=422, details=_details)


class UnauthorizedAction(FunctionalError):
    """
    Raised when permission is denied.

    Note: Use 401 for authentication failures, 403 for authorization.
    """

    def __init__(
        self,
        message: str = "Unauthorized action",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details.copy() if details else {}
        if required_permission:
            _details["required_permission"] = required_permission

        super().__init__(
            message,
            error_code="unauthorized_action",
            status_code=403,  # ARCHITECT NOTE 7: Use 403 for authorization
            details=_details,
        )


class AuthenticationError(FunctionalError):
    """
    Raised when authentication fails (missing or invalid credentials).
    Maps to HTTP 401 Unauthorized.
    """

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="authentication_failed", status_code=401, details=details)


class RateLimitError(FunctionalError):
    """
    Raised when the client has sent too many requests.
    Maps to HTTP 429 Too Many Requests.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details.copy() if details else {}
        if retry_after is not None:
            _details["retry_after"] = retry_after

        super().__init__(message, error_code="rate_limit_exceeded", status_code=429, details=_details)


# ============================================================================
# TECHNICAL ERRORS (5xx)
# ============================================================================


class ConfigurationError(TechnicalError):
    """Raised when critical configuration is missing or invalid."""

    def __init__(
        self,
        message: str = "Configuration Error",
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details.copy() if details else {}
        if config_key:
            _details["config_key"] = config_key

        super().__init__(message, error_code="configuration_error", status_code=500, details=_details)


class ExternalDependencyError(TechnicalError):
    """Raised when an external service (LLM, Vector DB, API) fails."""

    def __init__(
        self,
        message: str = "External service unavailable",
        service: str = "unknown",
        error_code: str = "external_dependency_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        # ARCHITECT NOTE 8: Consistent snake_case for error_code
        _details = details.copy() if details else {}
        _details["failed_service"] = service

        super().__init__(message, error_code=error_code, status_code=503, details=_details)


class InternalDataCorruption(TechnicalError):
    """
    Raised when DB constraints are violated unexpectedly
    or data is inconsistent.

    This indicates a critical system integrity issue.
    """

    def __init__(self, message: str = "Data integrity check failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="internal_data_corruption", status_code=500, details=details)


class FileSystemError(TechnicalError):
    """Raised when filesystem operations fail."""

    def __init__(
        self,
        message: str = "File system operation failed",
        file_path: Optional[str] = None,
        error_code: str = "filesystem_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details.copy() if details else {}
        if file_path:
            _details["file_path"] = file_path

        super().__init__(message, error_code=error_code, status_code=500, details=_details)
