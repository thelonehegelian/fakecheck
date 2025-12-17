"""
Configuration management for FakeCheck API.
"""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""

    # API Configuration
    app_name: str = Field(default="FakeCheck API", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # External API Keys
    anthropic_api_key: str = Field(..., description="Anthropic API key", validation_alias="ANTHROPIC_API_KEY")
    perplexity_api_key: str = Field(..., description="Perplexity API key", validation_alias="PERPLEXITY_API_KEY")

    # Model Configuration
    anthropic_model: str = Field(
        default="claude-3-5-haiku-latest", description="Anthropic model to use", validation_alias="ANTHROPIC_MODEL"
    )
    perplexity_model: str = Field(
        default="sonar-pro", description="Perplexity model to use", validation_alias="PERPLEXITY_MODEL"
    )

    # API Configuration
    max_tokens: int = Field(default=4000, description="Max tokens for AI responses")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
        validation_alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # Rate Limiting (future enhancement)
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # Custom Prompts
    base_prompt: Optional[str] = Field(default=None, description="Custom base prompt", validation_alias="BASE_PROMPT")

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @validator("anthropic_model")
    def validate_anthropic_model(cls, v):
        """Validate Anthropic model name."""
        valid_models = [
            "claude-3-5-haiku-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-opus-latest",
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
        ]
        if v not in valid_models:
            # Allow custom models, just warn
            print(f"Warning: Using custom Anthropic model: {v}")
        return v

    @validator("perplexity_model")
    def validate_perplexity_model(cls, v):
        """Validate Perplexity model name."""
        valid_models = ["sonar-pro", "sonar", "sonar-reasoning", "sonar-reasoning-pro"]
        if v not in valid_models:
            print(f"Warning: Using custom Perplexity model: {v}")
        return v

    def get_default_base_prompt(self) -> str:
        """Get the default base prompt."""
        return """You are a Fake News Detector. USING THE NEWS and the CONTEXT provided:

1. Rate the claim on a fake news meter, from 1-5 (where 5 is definitely fake)
2. Explain why it is likely to be fake. Give statistics and facts if available
3. Explain why it is possible that it might be true. Give statistics and facts if available
4. Make suggestions for the steps a user should take to further research these claims. 
   Identify specific things they should look for, don't give generic advice. 
   List them from easiest to do to more complex tasks and approximate the time for each task

YOU MUST MAINTAIN AN IMPARTIAL AND FAIR TONE."""

    def get_base_prompt(self) -> str:
        """Get the base prompt (custom or default)."""
        return self.base_prompt or self.get_default_base_prompt()

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
