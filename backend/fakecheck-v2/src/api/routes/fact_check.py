"""
Fact-checking API routes with proper versioning and error handling.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.core.config import Settings, get_settings
from src.core.exceptions import (
    FakeCheckError,
    ValidationError,
    ProcessingError,
    TimeoutError,
    ExternalAPIError,
    RateLimitError,
)
from src.services.fact_checker import FactCheckService
from src.models.requests import FactCheckRequest
from src.models.responses import (
    FactCheckResponse,
    ErrorResponse,
    HealthCheckResponse,
    APIInfoResponse,
)

logger = logging.getLogger(__name__)

# Create router with versioning
router = APIRouter(prefix="/v1", tags=["Fact Checking"])


def get_fact_check_service(
    settings: Settings = Depends(get_settings),
) -> FactCheckService:
    """Dependency to get fact-checking service."""
    return FactCheckService(settings)


async def log_request(request: Request):
    """Log incoming requests for monitoring."""
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    return request


@router.post(
    "/check-fake",
    response_model=FactCheckResponse,
    responses={
        200: {"description": "Fact-checking analysis completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "External API error"},
    },
    summary="Fact-check news content",
    description="Analyze news content for accuracy using AI research and analysis",
)
async def check_fake_news(
    request: FactCheckRequest,
    fact_check_service: FactCheckService = Depends(get_fact_check_service),
    req: Request = Depends(log_request),
):
    """
    Fact-check news content using AI research and analysis.

    This endpoint:
    1. Researches the claim using Perplexity Sonar API
    2. Analyzes the content using Anthropic Claude
    3. Returns a structured analysis with rating, explanations, and verification steps

    Args:
        request: The fact-checking request containing news content

    Returns:
        Structured fact-checking analysis
    """
    try:
        # Validate request
        if not request.news or len(request.news.strip()) < 10:
            raise ValidationError("News content must be at least 10 characters long")

        # Perform fact-checking
        result = await fact_check_service.check_news(request)

        # Return successful response
        return JSONResponse(
            content=result,
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=400)

    except TimeoutError as e:
        logger.error(f"Timeout error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=408)

    except RateLimitError as e:
        logger.warning(f"Rate limit error: {e.message}")
        headers = {}
        if e.details.get("retry_after"):
            headers["Retry-After"] = str(e.details["retry_after"])

        return JSONResponse(content=e.to_dict(), status_code=429, headers=headers)

    except ExternalAPIError as e:
        logger.error(f"External API error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=502)

    except ProcessingError as e:
        logger.error(f"Processing error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=500)

    except FakeCheckError as e:
        logger.error(f"FakeCheck error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=500)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # Following user rules: Never log complete errors
        error_response = FakeCheckError(
            "An unexpected error occurred during processing", "INTERNAL_ERROR"
        )
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
    summary="Health check",
    description="Check the health status of the fact-checking service and its dependencies",
)
async def health_check(
    fact_check_service: FactCheckService = Depends(get_fact_check_service),
    settings: Settings = Depends(get_settings),
):
    """
    Check the health of the fact-checking service.

    Returns:
        Health status including external service availability
    """
    try:
        # Perform health check
        health_results = await fact_check_service.health_check()

        # Determine overall status
        overall_status = health_results.get("overall", {}).get("status", "unhealthy")

        # Build response
        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "services": {
                service_name: service_info.get("status", "unknown")
                for service_name, service_info in health_results.items()
                if service_name != "overall"
            },
        }

        # Return appropriate status code
        status_code = 200 if overall_status == "healthy" else 503
        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "error": "Health check failed",
        }
        return JSONResponse(content=error_response, status_code=503)


@router.get(
    "/info",
    response_model=APIInfoResponse,
    responses={
        200: {"description": "API information"},
    },
    summary="API information",
    description="Get information about the fact-checking API",
)
async def get_api_info(
    fact_check_service: FactCheckService = Depends(get_fact_check_service),
    settings: Settings = Depends(get_settings),
):
    """
    Get information about the fact-checking API.

    Returns:
        API information including version, endpoints, and capabilities
    """
    try:
        service_info = fact_check_service.get_service_info()

        response_data = {
            "name": service_info["name"],
            "version": service_info["version"],
            "description": "A fact-checking service using AI research and analysis",
            "endpoints": ["/v1/check-fake", "/v1/health", "/v1/info"],
            "models": service_info["models"],
            "current_models": service_info["current_models"],
            "limits": service_info["limits"],
            "rate_limits": {
                "requests_per_minute": settings.rate_limit_requests,
                "window_seconds": settings.rate_limit_window,
            },
        }

        return JSONResponse(content=response_data, status_code=200)

    except Exception as e:
        logger.error(f"Failed to get API info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get API information")


# Add a simple root endpoint for the v1 API
@router.get(
    "/", summary="API root", description="Root endpoint for the fact-checking API v1"
)
async def api_root():
    """Root endpoint for the fact-checking API v1."""
    return {
        "message": "FakeCheck API v1",
        "version": "1.0.0",
        "endpoints": {
            "fact_check": "/v1/check-fake",
            "health": "/v1/health",
            "info": "/v1/info",
        },
        "documentation": "/docs",
    }
