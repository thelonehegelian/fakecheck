"""
Perplexica API client for fact-checking research using open-source AI search.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx

from src.core.config import Settings
from src.core.exceptions import (
    PerplexicaConnectionError,
    PerplexicaAPIError,
    TimeoutError,
    ProcessingError,
)

logger = logging.getLogger(__name__)


class PerplexicaClient:
    """Async client for Perplexica API (open-source AI search engine)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.endpoint = settings.perplexica_endpoint
        self.focus_mode = settings.perplexica_focus_mode
        self.optimization_mode = settings.perplexica_optimization_mode
        self.timeout = settings.request_timeout

        # Initialize async HTTP client
        self.client = httpx.AsyncClient(timeout=self.timeout)

        # Provider cache - will be populated on first request
        self._provider_id: Optional[str] = None  # For backward compatibility
        self._chat_provider_id: Optional[str] = None
        self._embedding_provider_id: Optional[str] = None
        self._chat_model_key: Optional[str] = None
        self._embedding_model_key: Optional[str] = None
        self._providers_cached = False

    async def _fetch_providers(self) -> Dict[str, Any]:
        """
        Fetch available providers from Perplexica API.

        Returns:
            Dictionary containing providers information

        Raises:
            PerplexicaConnectionError: When connection to Perplexica fails
            PerplexicaAPIError: When API returns an error
        """
        try:
            url = f"{self.endpoint}/api/providers"
            logger.info(f"Fetching providers from Perplexica: {url}")

            response = await self.client.get(url)
            response.raise_for_status()

            providers_data = response.json()
            logger.info(f"Successfully fetched providers from Perplexica")

            return providers_data

        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to Perplexica at {self.endpoint}: {str(e)}"
            logger.error(error_msg)
            raise PerplexicaConnectionError(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Perplexica request timed out after {self.timeout}s"
            logger.error(error_msg)
            raise TimeoutError(error_msg, timeout_seconds=self.timeout)
        except httpx.HTTPStatusError as e:
            error_msg = f"Perplexica API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise PerplexicaAPIError(error_msg, status_code=e.response.status_code)
        except Exception as e:
            error_msg = f"Unexpected error fetching providers: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)

    async def _initialize_providers(self) -> None:
        """
        Initialize provider cache by fetching available providers.
        Finds providers with chat and embedding models (can be different providers).
        """
        if self._providers_cached:
            return

        providers_data = await self._fetch_providers()
        providers = providers_data.get("providers", [])

        if not providers:
            raise PerplexicaAPIError("No providers available from Perplexica")

        # Find a provider with chat models
        # Prefer general-purpose models over specialized ones (guards, whisper, etc.)
        preferred_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "qwen/qwen3-32b",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ]

        chat_provider = None
        chat_provider_name = None
        for provider in providers:
            chat_models = provider.get("chatModels", [])
            if not chat_models:
                continue

            # Try to find a preferred model first
            selected_model = None
            for preferred in preferred_models:
                for model in chat_models:
                    if model["key"] == preferred:
                        selected_model = model["key"]
                        break
                if selected_model:
                    break

            # If no preferred model found, use the first available
            if not selected_model:
                selected_model = chat_models[0]["key"]

            chat_provider = provider
            chat_provider_name = provider.get("name", "Unknown")
            self._chat_model_key = selected_model
            break

        if not chat_provider:
            raise PerplexicaAPIError("No chat models available from any Perplexica provider")

        # Find a provider with embedding models (prefer same provider as chat if possible)
        embedding_provider = None
        embedding_provider_name = None

        # First, check if the chat provider also has embedding models
        if chat_provider.get("embeddingModels"):
            embedding_provider = chat_provider
            embedding_provider_name = chat_provider_name
        else:
            # Otherwise, find any provider with embedding models
            for provider in providers:
                embedding_models = provider.get("embeddingModels", [])
                if embedding_models:
                    embedding_provider = provider
                    embedding_provider_name = provider.get("name", "Unknown")
                    break

        if not embedding_provider:
            raise PerplexicaAPIError("No embedding models available from any Perplexica provider")

        # Set the embedding model
        embedding_models = embedding_provider.get("embeddingModels", [])
        self._embedding_model_key = embedding_models[0]["key"]

        # Store provider IDs (using a dict to support different providers)
        self._chat_provider_id = chat_provider["id"]
        self._embedding_provider_id = embedding_provider["id"]
        # Keep this for backward compatibility with get_available_models
        self._provider_id = chat_provider["id"]

        logger.info(
            f"Initialized Perplexica providers - "
            f"Chat: {chat_provider_name} ({self._chat_model_key}), "
            f"Embedding: {embedding_provider_name} ({self._embedding_model_key})"
        )

        self._providers_cached = True

    async def research_claim(
        self,
        text: str,
        model: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Research a claim using Perplexica API.

        Args:
            text: The claim or article to research
            model: Optional model override (not used for Perplexica, kept for interface compatibility)
            custom_prompt: Optional custom system instructions

        Returns:
            Dictionary containing research results and citations:
            {
                "content": str,
                "citations": List[str],
                "model_used": str,
                "usage": dict
            }

        Raises:
            PerplexicaConnectionError: When connection fails
            PerplexicaAPIError: When API returns an error
            ProcessingError: When content is empty or processing fails
        """
        if not text or not text.strip():
            raise ProcessingError("Cannot research empty text")

        # Initialize providers if not already done
        await self._initialize_providers()

        try:
            url = f"{self.endpoint}/api/search"
            logger.info(f"Sending research request to Perplexica: {url}")

            # Build request payload
            payload = {
                "chatModel": {
                    "providerId": self._chat_provider_id,
                    "key": self._chat_model_key,
                },
                "embeddingModel": {
                    "providerId": self._embedding_provider_id,
                    "key": self._embedding_model_key,
                },
                "optimizationMode": self.optimization_mode,
                "focusMode": self.focus_mode,
                "query": text,
                "stream": False,
            }

            # Add custom system instructions if provided
            if custom_prompt:
                payload["systemInstructions"] = custom_prompt

            logger.debug(f"Perplexica request payload: {payload}")

            # Send request
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Perplexica response: {result}")

            # Parse response to match SonarClient format
            message = result.get("message", "")
            sources = result.get("sources", [])

            # Extract citations from sources
            citations = [
                source.get("metadata", {}).get("url", "")
                for source in sources
                if source.get("metadata", {}).get("url")
            ]

            logger.info(
                f"Perplexica research completed. Found {len(citations)} citations"
            )

            return {
                "content": message,
                "citations": citations,
                "model_used": self._chat_model_key,
                "usage": {},  # Perplexica doesn't return token usage
            }

        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to Perplexica at {self.endpoint}: {str(e)}"
            logger.error(error_msg)
            raise PerplexicaConnectionError(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Perplexica request timed out after {self.timeout}s"
            logger.error(error_msg)
            raise TimeoutError(error_msg, timeout_seconds=self.timeout)
        except httpx.HTTPStatusError as e:
            error_msg = f"Perplexica API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise PerplexicaAPIError(error_msg, status_code=e.response.status_code)
        except KeyError as e:
            error_msg = f"Unexpected response format from Perplexica: missing key {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during Perplexica research: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the Perplexica API is accessible.

        Returns:
            Dictionary with health status:
            {
                "status": "healthy"|"unhealthy",
                "models_available": bool,
                "endpoint": str
            }
        """
        try:
            # Try to fetch providers as a health check
            providers_data = await self._fetch_providers()
            providers = providers_data.get("providers", [])

            models_available = bool(providers)

            return {
                "status": "healthy",
                "models_available": models_available,
                "endpoint": self.endpoint,
                "providers_count": len(providers),
            }

        except (PerplexicaConnectionError, PerplexicaAPIError, TimeoutError) as e:
            logger.warning(f"Perplexica health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "models_available": False,
                "endpoint": self.endpoint,
            }
        except Exception as e:
            logger.error(f"Unexpected error during Perplexica health check: {str(e)}")
            return {
                "status": "unhealthy",
                "error": f"Unexpected error: {str(e)}",
                "models_available": False,
                "endpoint": self.endpoint,
            }

    def get_available_models(self) -> List[str]:
        """
        Get list of available Perplexica models.

        Returns:
            List of model names (empty if providers not yet cached)
        """
        if self._providers_cached and self._chat_model_key:
            return [self._chat_model_key]
        return []

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self.client.aclose()
