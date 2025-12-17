"""
FakeCheck API - A fact-checking service using AI and web research.

This is the main entry point for the FakeCheck API v2.0.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.core.logging import setup_logging, with_correlation_id, generate_correlation_id
from src.core.exceptions import FakeCheckError
from src.api.routes.fact_check import router as fact_check_router

# Initialize settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger = logging.getLogger(__name__)
    logger.info("Starting FakeCheck API v2.0...")

    # Validate configuration
    try:
        # Test API keys are available
        assert settings.anthropic_api_key, "ANTHROPIC_API_KEY is required"
        assert settings.perplexity_api_key, "PERPLEXITY_API_KEY is required"
        logger.info("Configuration validated successfully")
    except AssertionError as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)

    logger.info("FakeCheck API v2.0 started successfully")

    yield

    # Shutdown
    logger.info("Shutting down FakeCheck API v2.0...")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to all requests."""

    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID for request
        correlation_id = generate_correlation_id()

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Process request with correlation ID context
        with with_correlation_id(correlation_id):
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Set up logging first
    setup_logging(settings)

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description="A fact-checking service using AI research and analysis",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Add custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Include routers
    app.include_router(fact_check_router)

    # Add global exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors."""
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {exc}"
        )

        error_response = FakeCheckError(
            "Invalid request data", "VALIDATION_ERROR", {"details": exc.errors()}
        )

        return JSONResponse(status_code=422, content=error_response.to_dict())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger = logging.getLogger(__name__)
        logger.warning(
            f"HTTP error on {request.method} {request.url.path}: {exc.status_code}"
        )

        error_response = FakeCheckError(
            exc.detail or "HTTP error occurred",
            "HTTP_ERROR",
            {"status_code": exc.status_code},
        )

        return JSONResponse(
            status_code=exc.status_code, content=error_response.to_dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        logger = logging.getLogger(__name__)
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}"
        )

        # Following user rules: Never log complete errors
        error_response = FakeCheckError(
            "An internal server error occurred", "INTERNAL_ERROR"
        )

        return JSONResponse(status_code=500, content=error_response.to_dict())

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint for the FakeCheck API."""
        return {
            "message": "FakeCheck API v2.0",
            "description": "A fact-checking service using AI research and analysis",
            "version": settings.app_version,
            "docs": "/docs",
            "api": {"v1": "/v1/"},
        }

    # Health check endpoint (also available at root level)
    @app.get("/health", tags=["Health"])
    async def health():
        """Simple health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": "2024-01-01T00:00:00Z",  # This would be actual timestamp
        }

    return app


# Create the app instance
app = create_app()


# For development purposes, add a simple test endpoint
if settings.debug:

    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Debug endpoint to check configuration (only in debug mode)."""
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "anthropic_model": settings.anthropic_model,
            "perplexity_model": settings.perplexity_model,
            "cors_origins": settings.cors_origins,
            "log_level": settings.log_level,
            "max_tokens": settings.max_tokens,
            "request_timeout": settings.request_timeout,
        }


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )
