"""
Anthropic Claude API client for fact-checking analysis.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import ClientTimeout, ClientSession

from src.core.config import Settings
from src.core.exceptions import (
    AnthropicAPIError,
    TimeoutError,
    ProcessingError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Async client for Anthropic Claude API."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model
        self.max_tokens = settings.max_tokens
        self.timeout = ClientTimeout(total=settings.request_timeout)

        # Define the schema for structured output
        self.article_schema = {
            "type": "object",
            "properties": {
                "fake_news_rating": {
                    "type": "integer",
                    "description": "Rating from 1-5 where 5 is definitely fake",
                    "minimum": 1,
                    "maximum": 5,
                },
                "fake_news_explanation": {
                    "type": "string",
                    "description": "Explanation of why the news might be fake, including statistics and facts",
                },
                "true_news_explanation": {
                    "type": "string",
                    "description": "Explanation of why the news might be true, including statistics and facts",
                },
                "verification_steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {
                                "type": "string",
                                "description": "Description of the verification step",
                            },
                            "estimated_time": {
                                "type": "string",
                                "description": "Estimated time to complete this step",
                            },
                            "complexity": {
                                "type": "string",
                                "enum": ["easy", "medium", "complex"],
                                "description": "Complexity level of the step",
                            },
                        },
                        "required": ["step", "estimated_time", "complexity"],
                    },
                },
            },
            "required": [
                "fake_news_rating",
                "fake_news_explanation",
                "true_news_explanation",
                "verification_steps",
            ],
        }

    async def analyze_news(
        self,
        news_text: str,
        research_context: str,
        citations: List[str],
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze news using Claude with structured output.

        Args:
            news_text: The news article or claim to analyze
            research_context: Research context from Perplexity
            citations: List of citation sources
            custom_prompt: Optional custom system prompt

        Returns:
            Structured analysis result

        Raises:
            AnthropicAPIError: When API call fails
            TimeoutError: When request times out
            ProcessingError: When response processing fails
        """
        if not news_text or not news_text.strip():
            raise ProcessingError("Cannot analyze empty news text")

        system_prompt = custom_prompt or self.settings.get_base_prompt()

        # Prepare the message content
        user_message = f"""News to analyze: {news_text}

Research context: {research_context}

Citations: {json.dumps(citations)}"""

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Define the tool for structured output
        tools = [
            {
                "name": "format_article",
                "description": "Structure news fact-check analysis with ratings, explanations, and verification steps",
                "input_schema": self.article_schema,
            }
        ]

        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "format_article"},
        }

        try:
            async with ClientSession(timeout=self.timeout) as session:
                logger.info(
                    f"Sending analysis request to Anthropic Claude with model: {self.model}"
                )

                async with session.post(
                    self.API_URL, headers=headers, json=data
                ) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        raise RateLimitError(
                            "Anthropic API rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None,
                        )

                    # Handle other HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            f"Anthropic API error {response.status}: {error_text}"
                        )
                        raise AnthropicAPIError(
                            f"Anthropic API request failed: {error_text}",
                            status_code=response.status,
                        )

                    result = await response.json()

                    # Process the structured response
                    return self._process_response(result, citations)

        except asyncio.TimeoutError:
            logger.error(
                f"Anthropic API request timed out after {self.settings.request_timeout}s"
            )
            raise TimeoutError(
                "Anthropic API request timed out",
                timeout_seconds=self.settings.request_timeout,
            )

        except aiohttp.ClientError as e:
            logger.error(f"Anthropic API client error: {str(e)}")
            raise AnthropicAPIError(f"API request failed: {str(e)}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic API response: {str(e)}")
            raise ProcessingError(f"Failed to parse API response: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in Anthropic API call: {str(e)}")
            raise ProcessingError(f"Unexpected error: {str(e)}")

    def _process_response(
        self, result: Dict[str, Any], citations: List[str]
    ) -> Dict[str, Any]:
        """
        Process the API response and extract structured data.

        Args:
            result: Raw API response
            citations: Original citations to include

        Returns:
            Processed response with structured data

        Raises:
            ProcessingError: When response format is unexpected
        """
        try:
            # Extract the tool use response
            if "content" in result and result["content"]:
                content = result["content"]

                # Find the tool use content
                for item in content:
                    if (
                        item.get("type") == "tool_use"
                        and item.get("name") == "format_article"
                    ):
                        tool_response = item.get("input", {})

                        # Add citations to the response
                        if citations:
                            tool_response["citations"] = citations

                        # Add metadata
                        tool_response["model_used"] = result.get("model", self.model)
                        tool_response["usage"] = result.get("usage", {})

                        return tool_response

                # If no tool use found, raise error
                raise ProcessingError("No tool use found in response")

            # If no content, return error
            raise ProcessingError("Unexpected API response format - no content found")

        except KeyError as e:
            logger.error(f"Missing key in API response: {str(e)}")
            raise ProcessingError(f"Invalid API response format: missing {str(e)}")

        except Exception as e:
            logger.error(f"Error processing API response: {str(e)}")
            raise ProcessingError(f"Failed to process API response: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the Anthropic API is accessible.

        Returns:
            Dictionary with health status
        """
        try:
            # Use a simple test query
            test_result = await self.analyze_news(
                "Test news: The Earth is round.",
                "Test context: Scientific consensus supports this fact.",
                ["NASA", "Scientific community"],
            )

            return {
                "status": "healthy",
                "response_time_ms": None,  # Could add timing here
                "model_available": True,
                "structured_output_available": "fake_news_rating" in test_result,
            }

        except Exception as e:
            logger.warning(f"Anthropic health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_available": False,
                "structured_output_available": False,
            }

    def get_available_models(self) -> List[str]:
        """
        Get list of available Anthropic models.

        Returns:
            List of model names
        """
        return [
            "claude-3-5-haiku-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-opus-latest",
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
        ]

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
