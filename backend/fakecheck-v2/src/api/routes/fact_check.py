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
from src.services.source_credibility import SourceCredibilityService
from src.services.claim_extraction import ClaimExtractionService
from src.models.requests import (
    FactCheckRequest,
    BatchFactCheckRequest,
    SourceCredibilityRequest,
    ClaimExtractionRequest,
)
from src.models.responses import (
    FactCheckResponse,
    BatchFactCheckResponse,
    SourceCredibilityResponse,
    ClaimExtractionResponse,
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


def get_source_credibility_service(
    settings: Settings = Depends(get_settings),
) -> SourceCredibilityService:
    """Dependency to get source credibility service."""
    return SourceCredibilityService(settings)


def get_claim_extraction_service(
    settings: Settings = Depends(get_settings),
) -> ClaimExtractionService:
    """Dependency to get claim extraction service."""
    return ClaimExtractionService(settings)


def log_request(request: Request) -> Request:
    """Log request details."""
    logger.info(f"Request: {request.method} {request.url.path}")
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
    summary="Enhanced fact-check news content",
    description="Analyze news content for accuracy using AI research, source credibility analysis, and claim extraction",
)
async def check_fake_news(
    request: FactCheckRequest,
    fact_check_service: FactCheckService = Depends(get_fact_check_service),
    req: Request = Depends(log_request),
):
    """
    Enhanced fact-check news content using AI research and analysis.

    Phase 1 enhancements include:
    - Automatic claim extraction from content
    - Source credibility analysis for URLs found in content
    - Confidence intervals for analysis results
    - Risk factor identification
    - Enhanced response format with additional metadata

    Args:
        request: The fact-checking request containing news content

    Returns:
        Structured fact-checking analysis with enhanced features
    """
    try:
        # Validate request
        if not request.news or len(request.news.strip()) < 10:
            raise ValidationError("News content must be at least 10 characters long")

        # Perform enhanced fact-checking
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


@router.post(
    "/check-fake/batch",
    response_model=BatchFactCheckResponse,
    responses={
        200: {"description": "Batch fact-checking completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Batch fact-check multiple news items",
    description="Process multiple news items simultaneously with enhanced analysis",
)
async def check_fake_news_batch(
    request: BatchFactCheckRequest,
    fact_check_service: FactCheckService = Depends(get_fact_check_service),
    req: Request = Depends(log_request),
):
    """
    Process multiple news items for fact-checking in a single request.

    Features:
    - Process up to 10 news items simultaneously
    - Parallel or sequential processing options
    - Batch summary with aggregated statistics
    - Individual error handling for each item
    - Enhanced analysis for each item

    Args:
        request: Batch fact-checking request with multiple items

    Returns:
        Batch results with summary statistics
    """
    try:
        # Validate request
        if not request.items or len(request.items) == 0:
            raise ValidationError("At least one news item is required")

        if len(request.items) > 10:
            raise ValidationError("Maximum 10 items allowed per batch")

        # Perform batch fact-checking
        result = await fact_check_service.check_news_batch(request)

        # Return successful response
        return JSONResponse(
            content=result,
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    except ValidationError as e:
        logger.warning(f"Batch validation error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=400)

    except ProcessingError as e:
        logger.error(f"Batch processing error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=500)

    except Exception as e:
        logger.error(f"Unexpected batch error: {str(e)}")
        error_response = FakeCheckError(
            "An unexpected error occurred during batch processing", "BATCH_ERROR"
        )
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@router.post(
    "/source-credibility",
    response_model=SourceCredibilityResponse,
    responses={
        200: {"description": "Source credibility analysis completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Analyze source credibility",
    description="Analyze the credibility and bias of a news source",
)
async def analyze_source_credibility(
    request: SourceCredibilityRequest,
    source_service: SourceCredibilityService = Depends(get_source_credibility_service),
    req: Request = Depends(log_request),
):
    """
    Analyze the credibility of a news source.

    Features:
    - Credibility scoring (0-100 scale)
    - Political bias detection
    - Factual accuracy assessment
    - Transparency scoring
    - Usage recommendations
    - Similar source suggestions

    Args:
        request: Source credibility request with URL, domain, or name

    Returns:
        Detailed source credibility analysis
    """
    try:
        # Perform source credibility analysis
        source_credibility = await source_service.analyze_source_credibility(
            source_url=request.source_url,
            source_domain=request.source_domain,
            source_name=request.source_name,
        )

        # Get recommendations
        recommendations = await source_service.get_source_recommendations(
            source_credibility
        )

        # Find similar sources
        similar_sources = await source_service.find_similar_sources(source_credibility)

        # Create summary
        if source_credibility.credibility_score >= 80:
            summary = f"{source_credibility.name or 'This source'} is highly credible with excellent factual accuracy."
        elif source_credibility.credibility_score >= 60:
            summary = f"{source_credibility.name or 'This source'} has good credibility but should be used with some caution."
        else:
            summary = f"{source_credibility.name or 'This source'} has limited credibility and requires verification."

        # Build response
        response_data = {
            "source_info": {
                "domain": source_credibility.domain,
                "name": source_credibility.name,
                "credibility_score": source_credibility.credibility_score,
                "bias_rating": source_credibility.bias_rating,
                "factual_accuracy": source_credibility.factual_accuracy,
                "transparency_score": source_credibility.transparency_score,
            },
            "analysis_summary": summary,
            "recommendations": recommendations,
            "similar_sources": [
                {
                    "domain": source.domain,
                    "name": source.name,
                    "credibility_score": source.credibility_score,
                    "bias_rating": source.bias_rating,
                    "factual_accuracy": source.factual_accuracy,
                }
                for source in similar_sources
            ]
            if similar_sources
            else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return JSONResponse(
            content=response_data,
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    except ValidationError as e:
        logger.warning(f"Source credibility validation error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=400)

    except ProcessingError as e:
        logger.error(f"Source credibility processing error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=500)

    except Exception as e:
        logger.error(f"Unexpected source credibility error: {str(e)}")
        error_response = FakeCheckError(
            "An unexpected error occurred during source analysis",
            "SOURCE_ANALYSIS_ERROR",
        )
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@router.post(
    "/extract-claims",
    response_model=ClaimExtractionResponse,
    responses={
        200: {"description": "Claim extraction completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Extract claims from text",
    description="Extract and analyze factual claims from news content",
)
async def extract_claims(
    request: ClaimExtractionRequest,
    claim_service: ClaimExtractionService = Depends(get_claim_extraction_service),
    req: Request = Depends(log_request),
):
    """
    Extract factual claims from text content.

    Features:
    - Automatic claim identification
    - Claim type classification (factual, opinion, statistical, etc.)
    - Confidence scoring for each claim
    - Verifiability assessment
    - Context extraction
    - Extraction summary with statistics

    Args:
        request: Claim extraction request with text and parameters

    Returns:
        List of extracted claims with analysis
    """
    try:
        # Perform claim extraction
        extracted_claims = await claim_service.extract_claims(
            text=request.text,
            extract_type=request.extract_type,
            max_claims=request.max_claims,
        )

        # Get extraction summary
        summary = await claim_service.get_extraction_summary(extracted_claims)

        # Build response
        response_data = {
            "extracted_claims": [
                {
                    "claim": claim.claim,
                    "claim_type": claim.claim_type,
                    "confidence": claim.confidence,
                    "verifiable": claim.verifiable,
                    "context": claim.context,
                }
                for claim in extracted_claims
            ],
            "extraction_summary": summary,
            "processing_time_ms": 0,  # Would be calculated if needed
            "timestamp": datetime.utcnow().isoformat(),
        }

        return JSONResponse(
            content=response_data,
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    except ValidationError as e:
        logger.warning(f"Claim extraction validation error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=400)

    except ProcessingError as e:
        logger.error(f"Claim extraction processing error: {e.message}")
        return JSONResponse(content=e.to_dict(), status_code=500)

    except Exception as e:
        logger.error(f"Unexpected claim extraction error: {str(e)}")
        error_response = FakeCheckError(
            "An unexpected error occurred during claim extraction",
            "CLAIM_EXTRACTION_ERROR",
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
            "endpoints": [
                "/v1/check-fake",
                "/v1/check-fake/batch",
                "/v1/source-credibility",
                "/v1/extract-claims",
                "/v1/health",
                "/v1/info",
            ],
            "models": service_info["models"],
            "current_models": service_info["current_models"],
            "limits": service_info["limits"],
            "features": service_info["features"],
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
        "message": "FakeCheck API v1 - Enhanced with Phase 1 Features",
        "version": "1.0.0",
        "endpoints": {
            "fact_check": "/v1/check-fake",
            "batch_fact_check": "/v1/check-fake/batch",
            "source_credibility": "/v1/source-credibility",
            "extract_claims": "/v1/extract-claims",
            "health": "/v1/health",
            "info": "/v1/info",
        },
        "documentation": "/docs",
        "phase_1_features": [
            "Batch processing",
            "Source credibility analysis",
            "Claim extraction",
            "Confidence intervals",
            "Risk factor identification",
        ],
    }
