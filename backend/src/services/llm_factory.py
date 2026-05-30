"""
LLM Provider Factory - selects the appropriate LLM client based on configuration.
"""

import logging
from typing import Union

from src.core.config import Settings
from src.services.anthropic_client import AnthropicClient
from src.services.groq_client import GroqClient
from src.services.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM clients based on configuration."""

    @staticmethod
    def create_client(settings: Settings) -> Union[AnthropicClient, GroqClient, OpenRouterClient]:
        """
        Create an LLM client based on the configured provider.

        Args:
            settings: Application settings

        Returns:
            LLM client instance (AnthropicClient, GroqClient, or OpenRouterClient)

        Raises:
            ValueError: If provider is invalid or API key is missing
        """
        provider = settings.llm_provider.lower()

        if provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY is required when LLM_PROVIDER is set to 'openrouter'"
                )
            model_name = settings.openrouter_model or "google/gemini-3.5-flash"
            logger.info("Using OpenRouter as LLM provider with model: %s", model_name)
            return OpenRouterClient(settings)

        elif provider == "groq":
            if not settings.groq_api_key:
                raise ValueError(
                    "GROQ_API_KEY is required when LLM_PROVIDER is set to 'groq'"
                )
            logger.info("Using Groq as LLM provider with model: %s", settings.groq_model)
            return GroqClient(settings)

        elif provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required when LLM_PROVIDER is set to 'anthropic'"
                )
            logger.info(
                "Using Anthropic as LLM provider with model: %s", settings.anthropic_model
            )
            return AnthropicClient(settings)

        else:
            raise ValueError(
                f"Invalid LLM provider: {provider}. Must be 'openrouter', 'groq', or 'anthropic'"
            )

    @staticmethod
    def get_provider_name(settings: Settings) -> str:
        """
        Get the name of the configured LLM provider.

        Args:
            settings: Application settings

        Returns:
            Provider name (e.g., "groq", "anthropic")
        """
        return settings.llm_provider.lower()

    @staticmethod
    def get_model_name(settings: Settings) -> str:
        """
        Get the model name for the configured provider.

        Args:
            settings: Application settings

        Returns:
            Model name
        """
        provider = settings.llm_provider.lower()
        if provider == "openrouter":
            return settings.openrouter_model or "google/gemini-3.5-flash"
        elif provider == "groq":
            return settings.groq_model
        elif provider == "anthropic":
            return settings.anthropic_model
        else:
            return "unknown"
