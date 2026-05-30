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
        # Test API keys are available based on provider/settings
        if settings.deployment == "hosted":
            assert settings.perplexica_enabled, "Perplexica must be enabled when deployment is hosted"
            assert not settings.research_fallback_enabled, "Perplexity fallback must be disabled when deployment is hosted"
            logger.info("Hosted deployment validation: Perplexica is enabled, fallback is disabled.")
        else:
            if not settings.perplexica_enabled or settings.research_fallback_enabled:
                assert settings.perplexity_api_key, "PERPLEXITY_API_KEY is required when Perplexica is disabled or fallback is enabled"

        llm_provider = settings.llm_provider.lower()
        if llm_provider == "openrouter":
            assert settings.openrouter_api_key, "OPENROUTER_API_KEY is required when using OpenRouter provider"
            logger.info(f"Using OpenRouter as LLM provider with model: {settings.openrouter_model}")
        elif llm_provider == "groq":
            assert settings.groq_api_key, "GROQ_API_KEY is required when using Groq provider"
            logger.info(f"Using Groq as LLM provider with model: {settings.groq_model}")
        elif llm_provider == "anthropic":
            assert settings.anthropic_api_key, "ANTHROPIC_API_KEY is required when using Anthropic provider"
            logger.info(f"Using Anthropic as LLM provider with model: {settings.anthropic_model}")

        logger.info("Configuration validated successfully")
    except AssertionError as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)

    # Start Reddit Bot in background if credentials are present
    if settings.reddit_client_id and settings.reddit_client_secret:
        try:
            from reddit_bot import RedditBot
            bot = RedditBot()
            bot.run_in_background()
            logger.info("Reddit Bot started in background")
        except Exception as e:
            logger.error(f"Failed to start Reddit Bot: {e}")

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


class ChromeExtensionAttestationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce origin and client attestation checks for hosted environments."""

    async def dispatch(self, request: Request, call_next):
        # We only protect the core fact-checking API routes
        protected_paths = [
            "/v1/check-fake",
            "/v1/check-fake/batch",
            "/v1/source-credibility",
            "/v1/extract-claims"
        ]

        # Only enforce checks in hosted deployments
        if settings.deployment == "hosted" and request.url.path in protected_paths:
            origin = request.headers.get("origin", "")
            user_agent = request.headers.get("user-agent", "").lower()

            # 1. Enforce that Origin strictly starts with chrome-extension://
            if not origin.startswith("chrome-extension://"):
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Blocked request to {request.url.path}: Missing or invalid Origin header '{origin}'"
                )
                error_response = FakeCheckError(
                    "Forbidden: Request must originate from the official Chrome Extension",
                    "FORBIDDEN_ORIGIN"
                )
                return JSONResponse(status_code=403, content=error_response.to_dict())

            # 2. Block generic script user agents (curl, python-requests, httpx, etc.)
            blocked_agents = ["curl", "python-requests", "httpx", "aiohttp", "go-http-client", "postman"]
            if not user_agent or any(agent in user_agent for agent in blocked_agents):
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Blocked request to {request.url.path}: Suspicious User-Agent '{user_agent}'"
                )
                error_response = FakeCheckError(
                    "Forbidden: Suspicious client signature detected",
                    "FORBIDDEN_CLIENT"
                )
                return JSONResponse(status_code=403, content=error_response.to_dict())

        return await call_next(request)


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
        allow_origin_regex=r"^chrome-extension://.*",
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Add custom middleware
    app.add_middleware(ChromeExtensionAttestationMiddleware)
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
            "deployment": settings.deployment,
            "llm_provider": settings.llm_provider,
            "openrouter_model": settings.openrouter_model,
            "groq_model": settings.groq_model,
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
