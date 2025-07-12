"""
Request models for FakeCheck API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from src.core.exceptions import EmptyContentError, ContentTooLargeError


class FactCheckRequest(BaseModel):
    """Request model for fact-checking endpoint."""

    news: str = Field(
        ...,
        description="The news article or claim to fact-check",
        example="The Great Wall of China is visible from space.",
    )

    # Optional parameters for customization
    custom_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt to use for fact-checking",
        max_length=1000,
    )

    priority: Optional[str] = Field(
        default="normal",
        description="Priority level for processing",
        pattern="^(low|normal|high)$",
    )

    @validator("news")
    def validate_news_content(cls, v):
        """Validate news content."""
        if not v or not v.strip():
            raise EmptyContentError("News content cannot be empty")

        # Check length limits
        if len(v) > 10000:  # 10KB limit
            raise ContentTooLargeError(
                "News content is too large", max_size=10000, actual_size=len(v)
            )

        # Check for minimum content
        if len(v.strip()) < 10:
            raise EmptyContentError("News content must be at least 10 characters")

        return v.strip()

    @validator("custom_prompt")
    def validate_custom_prompt(cls, v):
        """Validate custom prompt."""
        if v is not None and len(v) > 1000:
            raise ContentTooLargeError(
                "Custom prompt is too large", max_size=1000, actual_size=len(v)
            )
        return v

    class Config:
        """Pydantic configuration."""

        schema_extra = {
            "example": {
                "news": "Scientists have discovered that drinking 8 glasses of water per day is actually harmful to most people.",
                "custom_prompt": None,
                "priority": "normal",
            }
        }


class BatchFactCheckRequest(BaseModel):
    """Request model for batch fact-checking endpoint."""

    items: List[FactCheckRequest] = Field(
        ...,
        description="List of fact-checking requests to process",
        min_items=1,
        max_items=10,
    )

    batch_settings: Optional[dict] = Field(
        default=None, description="Batch processing settings"
    )

    @validator("items")
    def validate_batch_items(cls, v):
        """Validate batch items."""
        if len(v) > 10:
            raise ContentTooLargeError(
                "Too many items in batch", max_size=10, actual_size=len(v)
            )
        return v

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "news": "The Great Wall of China is visible from space.",
                        "priority": "normal",
                    },
                    {"news": "Vaccines cause autism in children.", "priority": "high"},
                ],
                "batch_settings": {
                    "parallel_processing": True,
                    "include_source_analysis": True,
                },
            }
        }


class SourceCredibilityRequest(BaseModel):
    """Request model for source credibility checking."""

    source_url: Optional[str] = Field(
        default=None,
        description="URL of the source to check",
        example="https://example.com/article",
    )

    source_domain: Optional[str] = Field(
        default=None, description="Domain of the source to check", example="example.com"
    )

    source_name: Optional[str] = Field(
        default=None,
        description="Name of the source to check",
        example="Example News Network",
    )

    @validator("source_url", "source_domain", "source_name")
    def validate_at_least_one_source(cls, v, values):
        """Validate that at least one source identifier is provided."""
        if not any(
            [
                v,
                values.get("source_url"),
                values.get("source_domain"),
                values.get("source_name"),
            ]
        ):
            raise EmptyContentError("At least one source identifier must be provided")
        return v

    class Config:
        schema_extra = {
            "example": {
                "source_url": "https://www.bbc.com/news/world",
                "source_domain": "bbc.com",
                "source_name": "BBC News",
            }
        }


class ClaimExtractionRequest(BaseModel):
    """Request model for claim extraction."""

    text: str = Field(
        ...,
        description="Text to extract claims from",
        example="Scientists have discovered that drinking 8 glasses of water per day is actually harmful. The study was published in the Journal of Medicine.",
    )

    extract_type: Optional[str] = Field(
        default="factual",
        description="Type of claims to extract",
        pattern="^(factual|opinion|statistical|all)$",
    )

    max_claims: Optional[int] = Field(
        default=5, description="Maximum number of claims to extract", ge=1, le=20
    )

    @validator("text")
    def validate_text_content(cls, v):
        """Validate text content."""
        if not v or not v.strip():
            raise EmptyContentError("Text content cannot be empty")

        if len(v) > 50000:  # 50KB limit for claim extraction
            raise ContentTooLargeError(
                "Text content is too large", max_size=50000, actual_size=len(v)
            )

        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "text": "Scientists have discovered that drinking 8 glasses of water per day is actually harmful. The study was published in the Journal of Medicine and involved 10,000 participants over 5 years.",
                "extract_type": "factual",
                "max_claims": 5,
            }
        }


class HealthCheckRequest(BaseModel):
    """Request model for health check endpoint."""

    include_details: Optional[bool] = Field(
        default=False, description="Whether to include detailed health information"
    )

    class Config:
        """Pydantic configuration."""

        schema_extra = {"example": {"include_details": False}}
