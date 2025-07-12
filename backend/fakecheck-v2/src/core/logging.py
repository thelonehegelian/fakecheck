"""
Structured logging configuration for FakeCheck API.
"""

import logging
import logging.config
import sys
import uuid
from contextvars import ContextVar
from typing import Dict, Any, Optional

from src.core.config import Settings


# Context variable to store correlation ID for request tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record."""
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "N/A"
        return True


class CustomFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def __init__(self, include_correlation_id: bool = True):
        self.include_correlation_id = include_correlation_id
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information."""
        # Base format
        base_format = "%(asctime)s - %(name)s - %(levelname)s"

        # Add correlation ID if enabled
        if self.include_correlation_id and hasattr(record, "correlation_id"):
            base_format += " - [%(correlation_id)s]"

        # Add message
        base_format += " - %(message)s"

        # Add exception info if present
        if record.exc_info:
            base_format += "\n%(exc_text)s"

        formatter = logging.Formatter(base_format)
        return formatter.format(record)


def setup_logging(settings: Settings) -> None:
    """
    Set up logging configuration.

    Args:
        settings: Application settings
    """
    # Create logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"()": CustomFormatter, "include_correlation_id": True},
            "simple": {"format": "%(levelname)s - %(message)s"},
        },
        "filters": {"correlation_id": {"()": CorrelationIdFilter}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard",
                "filters": ["correlation_id"],
                "stream": sys.stdout,
            }
        },
        "loggers": {
            # Root logger
            "": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Application loggers
            "src": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "src.services": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "src.api": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # External library loggers
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "aiohttp": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpx": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        },
    }

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.log_level}")


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.

    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.

    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.

    Returns:
        New correlation ID
    """
    return str(uuid.uuid4())


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    correlation_id_var.set(None)


class LoggingContextManager:
    """Context manager for handling correlation IDs in requests."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.previous_correlation_id = None

    def __enter__(self):
        self.previous_correlation_id = get_correlation_id()
        set_correlation_id(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_correlation_id:
            set_correlation_id(self.previous_correlation_id)
        else:
            clear_correlation_id()


def with_correlation_id(correlation_id: Optional[str] = None) -> LoggingContextManager:
    """
    Create a context manager with a correlation ID.

    Args:
        correlation_id: Optional correlation ID, generates one if not provided

    Returns:
        Context manager for logging with correlation ID
    """
    return LoggingContextManager(correlation_id)


# Utility functions for safe logging (following user rules)
def safe_log_error(
    logger: logging.Logger, message: str, error: Exception, **kwargs
) -> None:
    """
    Safely log an error without exposing sensitive information.

    Args:
        logger: Logger to use
        message: Base message
        error: Exception to log
        **kwargs: Additional context
    """
    # Only log the error type and basic message, not full details
    error_type = type(error).__name__
    safe_message = f"{message} - Error type: {error_type}"

    # Add safe context
    if kwargs:
        safe_context = {k: v for k, v in kwargs.items() if not k.startswith("_")}
        safe_message += f" - Context: {safe_context}"

    logger.error(safe_message)


def safe_log_request(logger: logging.Logger, method: str, path: str, **kwargs) -> None:
    """
    Safely log a request without exposing sensitive information.

    Args:
        logger: Logger to use
        method: HTTP method
        path: Request path
        **kwargs: Additional context
    """
    # Basic request information
    message = f"Request: {method} {path}"

    # Add safe context (no sensitive data)
    safe_context = {}
    for k, v in kwargs.items():
        if k in ["user_agent", "ip", "correlation_id", "processing_time"]:
            safe_context[k] = v

    if safe_context:
        message += f" - {safe_context}"

    logger.info(message)
