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
        ..., description="Complexity level of the step", pattern="^(easy|medium|complex)$"
    )

    class Config:
        schema_extra = {
            "example": {
                "step": "Check the original source of the claim",
                "estimated_time": "5 minutes",
                "complexity": "easy",
            }
        }


class SourceCredibility(BaseModel):
    """Model for source credibility information."""

    domain: Optional[str] = Field(default=None, description="Source domain")
    name: Optional[str] = Field(default=None, description="Source name")
    credibility_score: float = Field(
        ..., description="Credibility score from 0-100", ge=0, le=100
    )
    bias_rating: Optional[str] = Field(
        default=None,
        description="Political bias rating",
        pattern="^(left|center-left|center|center-right|right|unknown)$",
    )
    factual_accuracy: Optional[str] = Field(
        default=None,
        description="Factual accuracy rating",
        pattern="^(very-high|high|mostly-factual|mixed|low|very-low|unknown)$",
    )
    transparency_score: Optional[float] = Field(
        default=None, description="Transparency score from 0-100", ge=0, le=100
    )

    class Config:
        schema_extra = {
            "example": {
                "domain": "bbc.com",
                "name": "BBC News",
                "credibility_score": 85.5,
                "bias_rating": "center-left",
                "factual_accuracy": "high",
                "transparency_score": 92.0,
            }
        }


class ExtractedClaim(BaseModel):
    """Model for an extracted claim."""

    claim: str = Field(..., description="The extracted claim")
    claim_type: str = Field(
        ...,
        description="Type of claim",
        pattern="^(factual|opinion|statistical|prediction|other)$",
    )
    confidence: float = Field(
        ..., description="Confidence in claim extraction", ge=0, le=1
    )
    context: Optional[str] = Field(
        default=None, description="Context surrounding the claim"
    )
    verifiable: bool = Field(..., description="Whether the claim is verifiable")

    class Config:
        schema_extra = {
            "example": {
                "claim": "Drinking 8 glasses of water per day is harmful",
                "claim_type": "factual",
                "confidence": 0.9,
                "context": "Scientists have discovered that...",
                "verifiable": True,
            }
        }


class FactCheckResponse(BaseModel):
    """Enhanced response model for fact-checking endpoint."""

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

    # Enhanced metadata
    citations: Optional[List[str]] = Field(
        default=None, description="List of sources used for fact-checking"
    )

    processing_time_ms: Optional[int] = Field(
        default=None, description="Time taken to process the request in milliseconds"
    )

    confidence_score: Optional[float] = Field(
        default=None, description="Confidence score of the analysis (0-1)", ge=0, le=1
    )

    # New Phase 1 fields
    confidence_interval: Optional[Dict[str, float]] = Field(
        default=None, description="Confidence interval for the rating"
    )

    source_analysis: Optional[List[SourceCredibility]] = Field(
        default=None, description="Analysis of sources mentioned in the content"
    )

    extracted_claims: Optional[List[ExtractedClaim]] = Field(
        default=None, description="Key claims extracted from the content"
    )

    risk_factors: Optional[List[str]] = Field(
        default=None, description="Risk factors that might indicate misinformation"
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
                "confidence_interval": {"lower_bound": 0.75, "upper_bound": 0.95},
                "source_analysis": [
                    {
                        "domain": "who.int",
                        "name": "World Health Organization",
                        "credibility_score": 98.5,
                        "bias_rating": "center",
                        "factual_accuracy": "very-high",
                    }
                ],
                "extracted_claims": [
                    {
                        "claim": "8 glasses of water per day is harmful",
                        "claim_type": "factual",
                        "confidence": 0.95,
                        "verifiable": True,
                    }
                ],
                "risk_factors": [
                    "Contradicts established medical guidelines",
                    "Lacks peer-reviewed evidence",
                ],
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class BatchFactCheckResponse(BaseModel):
    """Response model for batch fact-checking endpoint."""

    total_items: int = Field(..., description="Total number of items processed")
    successful_items: int = Field(
        ..., description="Number of successfully processed items"
    )
    failed_items: int = Field(..., description="Number of failed items")

    results: List[Dict[str, Any]] = Field(
        ..., description="List of fact-checking results"
    )

    batch_summary: Dict[str, Any] = Field(
        ..., description="Summary of batch processing"
    )

    processing_time_ms: int = Field(
        ..., description="Total processing time in milliseconds"
    )

    timestamp: datetime = Field(
        ..., description="Timestamp when batch processing was completed"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_items": 2,
                "successful_items": 2,
                "failed_items": 0,
                "results": [
                    {
                        "item_id": 0,
                        "status": "success",
                        "result": {
                            "fake_news_rating": 4,
                            "fake_news_explanation": "This is a common misconception...",
                            "confidence_score": 0.85,
                        },
                    },
                    {
                        "item_id": 1,
                        "status": "success",
                        "result": {
                            "fake_news_rating": 5,
                            "fake_news_explanation": "This claim has been debunked...",
                            "confidence_score": 0.92,
                        },
                    },
                ],
                "batch_summary": {
                    "average_rating": 4.5,
                    "average_confidence": 0.885,
                    "most_common_risk_factors": ["Contradicts scientific consensus"],
                },
                "processing_time_ms": 8500,
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class SourceCredibilityResponse(BaseModel):
    """Response model for source credibility endpoint."""

    source_info: SourceCredibility = Field(
        ..., description="Detailed source credibility information"
    )

    analysis_summary: str = Field(
        ..., description="Summary of the credibility analysis"
    )

    recommendations: List[str] = Field(
        ..., description="Recommendations for using this source"
    )

    similar_sources: Optional[List[SourceCredibility]] = Field(
        default=None, description="Similar sources for comparison"
    )

    timestamp: datetime = Field(
        ..., description="Timestamp when the analysis was completed"
    )

    class Config:
        schema_extra = {
            "example": {
                "source_info": {
                    "domain": "bbc.com",
                    "name": "BBC News",
                    "credibility_score": 85.5,
                    "bias_rating": "center-left",
                    "factual_accuracy": "high",
                },
                "analysis_summary": "BBC News is a highly credible source with strong factual accuracy and minimal bias.",
                "recommendations": [
                    "Excellent for breaking news and international coverage",
                    "Generally reliable for factual information",
                    "Consider slight center-left bias in editorial content",
                ],
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class ClaimExtractionResponse(BaseModel):
    """Response model for claim extraction endpoint."""

    extracted_claims: List[ExtractedClaim] = Field(
        ..., description="List of extracted claims"
    )

    extraction_summary: Dict[str, Any] = Field(
        ..., description="Summary of extraction process"
    )

    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    timestamp: datetime = Field(
        ..., description="Timestamp when extraction was completed"
    )

    class Config:
        schema_extra = {
            "example": {
                "extracted_claims": [
                    {
                        "claim": "Drinking 8 glasses of water per day is harmful",
                        "claim_type": "factual",
                        "confidence": 0.95,
                        "verifiable": True,
                    },
                    {
                        "claim": "The study involved 10,000 participants",
                        "claim_type": "statistical",
                        "confidence": 0.88,
                        "verifiable": True,
                    },
                ],
                "extraction_summary": {
                    "total_claims_found": 2,
                    "factual_claims": 1,
                    "statistical_claims": 1,
                    "verifiable_claims": 2,
                },
                "processing_time_ms": 1200,
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
