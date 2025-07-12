"""
Request models for FakeCheck API.
"""

from typing import Optional
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
        regex="^(low|normal|high)$",
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


class HealthCheckRequest(BaseModel):
    """Request model for health check endpoint."""

    include_details: Optional[bool] = Field(
        default=False, description="Whether to include detailed health information"
    )

    class Config:
        """Pydantic configuration."""

        schema_extra = {"example": {"include_details": False}}
