"""
Response models for FakeCheck API.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class VerificationStep(BaseModel):
    """Model for a single verification step."""

    step: str = Field(..., description="Description of the verification step")
    estimated_time: str = Field(..., description="Estimated time to complete this step")
    complexity: str = Field(
        ..., description="Complexity level of the step", regex="^(easy|medium|complex)$"
    )

    class Config:
        schema_extra = {
            "example": {
                "step": "Check the original source of the claim",
                "estimated_time": "5 minutes",
                "complexity": "easy",
            }
        }


class FactCheckResponse(BaseModel):
    """Response model for fact-checking endpoint."""

    fake_news_rating: int = Field(
        ..., description="Rating from 1-5 where 5 is definitely fake", ge=1, le=5
    )

    fake_news_explanation: str = Field(
        ...,
        description="Explanation of why the news might be fake, including statistics and facts",
    )

    true_news_explanation: str = Field(
        ...,
        description="Explanation of why the news might be true, including statistics and facts",
    )

    verification_steps: List[VerificationStep] = Field(
        ..., description="List of steps to verify the claim"
    )

    # Additional metadata
    citations: Optional[List[str]] = Field(
        default=None, description="List of sources used for fact-checking"
    )

    processing_time_ms: Optional[int] = Field(
        default=None, description="Time taken to process the request in milliseconds"
    )

    confidence_score: Optional[float] = Field(
        default=None, description="Confidence score of the analysis (0-1)", ge=0, le=1
    )

    timestamp: Optional[datetime] = Field(
        default=None, description="Timestamp when the analysis was completed"
    )

    class Config:
        schema_extra = {
            "example": {
                "fake_news_rating": 4,
                "fake_news_explanation": "This claim lacks credible scientific evidence and contradicts established health guidelines from major medical organizations.",
                "true_news_explanation": "Some individuals may have specific medical conditions that require limited water intake, but this doesn't apply to the general population.",
                "verification_steps": [
                    {
                        "step": "Check WHO and CDC guidelines on daily water intake",
                        "estimated_time": "5 minutes",
                        "complexity": "easy",
                    },
                    {
                        "step": "Search for peer-reviewed studies on water intake recommendations",
                        "estimated_time": "15 minutes",
                        "complexity": "medium",
                    },
                ],
                "citations": [
                    "World Health Organization water intake guidelines",
                    "Mayo Clinic hydration recommendations",
                ],
                "processing_time_ms": 3500,
                "confidence_score": 0.85,
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """Response model for error cases."""

    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for programmatic handling")
    timestamp: datetime = Field(..., description="Timestamp when the error occurred")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )

    class Config:
        schema_extra = {
            "example": {
                "error": "News content cannot be empty",
                "error_code": "VALIDATION_ERROR",
                "timestamp": "2024-01-15T10:30:00Z",
                "details": {"field": "news"},
            }
        }


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    version: str = Field(..., description="API version")

    # Optional detailed information
    services: Optional[Dict[str, str]] = Field(
        default=None, description="Status of external services"
    )

    uptime_seconds: Optional[int] = Field(default=None, description="Uptime in seconds")

    memory_usage_mb: Optional[float] = Field(
        default=None, description="Memory usage in MB"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "2.0.0",
                "services": {"anthropic": "healthy", "perplexity": "healthy"},
                "uptime_seconds": 3600,
                "memory_usage_mb": 256.5,
            }
        }


class APIInfoResponse(BaseModel):
    """Response model for API info endpoint."""

    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")

    endpoints: List[str] = Field(..., description="Available endpoints")

    rate_limits: Optional[Dict[str, int]] = Field(
        default=None, description="Rate limit information"
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "FakeCheck API",
                "version": "2.0.0",
                "description": "A fact-checking service using AI and web research",
                "endpoints": ["/v1/check-fake", "/v1/health", "/v1/info"],
                "rate_limits": {"requests_per_minute": 100, "requests_per_hour": 1000},
            }
        }
