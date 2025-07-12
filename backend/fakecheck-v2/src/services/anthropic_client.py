"""
Anthropic Claude API client for fact-checking operations.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from src.core.config import Settings
from src.core.exceptions import (
    AnthropicAPIError,
    ProcessingError,
    RateLimitError,
    TimeoutError,
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

        # JSON schema for structured output
        self.article_schema = {
            "type": "object",
            "properties": {
                "fake_news_rating": {
                    "type": "integer",
                    "description": "Rating from 1-5 where 5 is definitely fake news",
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
                    "description": "List of steps to verify the claim",
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
                                "description": "Complexity level of the step",
                                "enum": ["easy", "medium", "complex"],
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
        Analyze news content using Anthropic Claude.

        Args:
            news_text: The news content to analyze
            research_context: Context from research
            citations: List of citations
            custom_prompt: Custom system prompt

        Returns:
            Dictionary with analysis results

        Raises:
            AnthropicAPIError: When API call fails
            ProcessingError: When response processing fails
            RateLimitError: When rate limit is exceeded
            TimeoutError: When request times out
        """
        # Get system prompt
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

    async def analyze_source_credibility(
        self, prompt: str, source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze source credibility using Anthropic Claude.

        Args:
            prompt: Analysis prompt
            source_info: Source information

        Returns:
            Dictionary with credibility analysis results

        Raises:
            AnthropicAPIError: When API call fails
            ProcessingError: When response processing fails
        """
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Define the tool for structured output
        tools = [
            {
                "name": "analyze_source",
                "description": "Analyze source credibility with structured output",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Source name"},
                        "credibility_score": {
                            "type": "number",
                            "description": "Credibility score 0-100",
                        },
                        "bias_rating": {"type": "string", "description": "Bias rating"},
                        "factual_accuracy": {
                            "type": "string",
                            "description": "Factual accuracy rating",
                        },
                        "transparency_score": {
                            "type": "number",
                            "description": "Transparency score 0-100",
                        },
                        "analysis_notes": {
                            "type": "string",
                            "description": "Analysis notes",
                        },
                    },
                    "required": [
                        "credibility_score",
                        "bias_rating",
                        "factual_accuracy",
                    ],
                },
            }
        ]

        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": "You are a media literacy expert analyzing news source credibility.",
            "messages": [{"role": "user", "content": prompt}],
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "analyze_source"},
        }

        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.API_URL, headers=headers, json=data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            f"Anthropic API error {response.status}: {error_text}"
                        )
                        raise AnthropicAPIError(f"Source analysis failed: {error_text}")

                    result = await response.json()
                    return self._process_tool_response(result, "analyze_source")

        except Exception as e:
            logger.error(f"Source credibility analysis failed: {str(e)}")
            raise ProcessingError(f"Failed to analyze source credibility: {str(e)}")

    async def extract_claims(
        self, prompt: str, text: str, extract_type: str = "factual", max_claims: int = 5
    ) -> Dict[str, Any]:
        """
        Extract claims from text using Anthropic Claude.

        Args:
            prompt: Extraction prompt
            text: Text to extract claims from
            extract_type: Type of claims to extract
            max_claims: Maximum number of claims

        Returns:
            Dictionary with extracted claims

        Raises:
            AnthropicAPIError: When API call fails
            ProcessingError: When response processing fails
        """
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Define the tool for structured output
        tools = [
            {
                "name": "extract_claims",
                "description": "Extract claims from text with structured output",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "claims": {
                            "type": "array",
                            "description": "List of extracted claims",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "claim": {
                                        "type": "string",
                                        "description": "The claim text",
                                    },
                                    "claim_type": {
                                        "type": "string",
                                        "description": "Type of claim",
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "description": "Confidence score 0-1",
                                    },
                                    "verifiable": {
                                        "type": "boolean",
                                        "description": "Whether verifiable",
                                    },
                                    "context": {
                                        "type": "string",
                                        "description": "Context around claim",
                                    },
                                },
                                "required": [
                                    "claim",
                                    "claim_type",
                                    "confidence",
                                    "verifiable",
                                ],
                            },
                        },
                        "summary": {
                            "type": "string",
                            "description": "Extraction summary",
                        },
                    },
                    "required": ["claims"],
                },
            }
        ]

        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": "You are an expert at extracting and analyzing claims from text content.",
            "messages": [{"role": "user", "content": prompt}],
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "extract_claims"},
        }

        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.API_URL, headers=headers, json=data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            f"Anthropic API error {response.status}: {error_text}"
                        )
                        raise AnthropicAPIError(
                            f"Claim extraction failed: {error_text}"
                        )

                    result = await response.json()
                    return self._process_tool_response(result, "extract_claims")

        except Exception as e:
            logger.error(f"Claim extraction failed: {str(e)}")
            raise ProcessingError(f"Failed to extract claims: {str(e)}")

    async def analyze_claim_verifiability(
        self, prompt: str, claim: str
    ) -> Dict[str, Any]:
        """
        Analyze how a claim can be verified using Anthropic Claude.

        Args:
            prompt: Analysis prompt
            claim: Claim to analyze

        Returns:
            Dictionary with verifiability analysis

        Raises:
            AnthropicAPIError: When API call fails
            ProcessingError: When response processing fails
        """
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Define the tool for structured output
        tools = [
            {
                "name": "analyze_verifiability",
                "description": "Analyze claim verifiability with structured output",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "verification_methods": {
                            "type": "array",
                            "description": "Methods to verify the claim",
                            "items": {"type": "string"},
                        },
                        "potential_sources": {
                            "type": "array",
                            "description": "Sources that could verify the claim",
                            "items": {"type": "string"},
                        },
                        "difficulty_level": {
                            "type": "string",
                            "description": "Difficulty of verification",
                        },
                        "time_estimate": {
                            "type": "string",
                            "description": "Time estimate for verification",
                        },
                        "key_terms": {
                            "type": "array",
                            "description": "Key terms for research",
                            "items": {"type": "string"},
                        },
                        "searchability_score": {
                            "type": "number",
                            "description": "How searchable is this claim",
                        },
                    },
                    "required": [
                        "verification_methods",
                        "potential_sources",
                        "difficulty_level",
                    ],
                },
            }
        ]

        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": "You are an expert fact-checker analyzing how claims can be verified.",
            "messages": [{"role": "user", "content": prompt}],
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "analyze_verifiability"},
        }

        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.API_URL, headers=headers, json=data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            f"Anthropic API error {response.status}: {error_text}"
                        )
                        raise AnthropicAPIError(
                            f"Verifiability analysis failed: {error_text}"
                        )

                    result = await response.json()
                    return self._process_tool_response(result, "analyze_verifiability")

        except Exception as e:
            logger.error(f"Claim verifiability analysis failed: {str(e)}")
            raise ProcessingError(f"Failed to analyze claim verifiability: {str(e)}")

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

    def _process_tool_response(
        self, result: Dict[str, Any], tool_name: str
    ) -> Dict[str, Any]:
        """
        Process a tool response from the API.

        Args:
            result: Raw API response
            tool_name: Name of the tool used

        Returns:
            Processed tool response

        Raises:
            ProcessingError: When response format is unexpected
        """
        try:
            if "content" in result and result["content"]:
                content = result["content"]

                # Find the tool use content
                for item in content:
                    if item.get("type") == "tool_use" and item.get("name") == tool_name:
                        tool_response = item.get("input", {})

                        # Add metadata
                        tool_response["model_used"] = result.get("model", self.model)
                        tool_response["usage"] = result.get("usage", {})

                        return tool_response

                # If no tool use found, raise error
                raise ProcessingError(f"No {tool_name} tool use found in response")

            # If no content, return error
            raise ProcessingError("Unexpected API response format - no content found")

        except KeyError as e:
            logger.error(f"Missing key in API response: {str(e)}")
            raise ProcessingError(f"Invalid API response format: missing {str(e)}")

        except Exception as e:
            logger.error(f"Error processing tool response: {str(e)}")
            raise ProcessingError(f"Failed to process tool response: {str(e)}")

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
