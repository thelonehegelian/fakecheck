"""
Custom exceptions for FakeCheck API.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class FakeCheckError(Exception):
    """Base exception for FakeCheck API errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class ConfigurationError(FakeCheckError):
    """Raised when there's a configuration issue."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class ValidationError(FakeCheckError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", error_details)


class ExternalAPIError(FakeCheckError):
    """Raised when external API calls fail."""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["service"] = service
        if status_code:
            error_details["status_code"] = status_code
        super().__init__(message, "EXTERNAL_API_ERROR", error_details)


class AnthropicAPIError(ExternalAPIError):
    """Raised when Anthropic API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "anthropic", status_code, details)


class PerplexityAPIError(ExternalAPIError):
    """Raised when Perplexity API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "perplexity", status_code, details)


class RateLimitError(FakeCheckError):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        super().__init__(message, "RATE_LIMIT_ERROR", error_details)


class ProcessingError(FakeCheckError):
    """Raised when fact-checking processing fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PROCESSING_ERROR", details)


class TimeoutError(FakeCheckError):
    """Raised when operations timeout."""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        super().__init__(message, "TIMEOUT_ERROR", error_details)


class ContentTooLargeError(ValidationError):
    """Raised when input content exceeds size limits."""

    def __init__(
        self,
        message: str = "Content too large",
        max_size: Optional[int] = None,
        actual_size: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if max_size:
            error_details["max_size"] = max_size
        if actual_size:
            error_details["actual_size"] = actual_size
        super().__init__(message, "content", error_details)


class EmptyContentError(ValidationError):
    """Raised when input content is empty."""

    def __init__(
        self,
        message: str = "Content cannot be empty",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "content", details)
