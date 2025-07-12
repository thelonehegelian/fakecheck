"""
Perplexity Sonar API client for fact-checking research.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import ClientTimeout, ClientSession

from src.core.config import Settings
from src.core.exceptions import (
    PerplexityAPIError,
    TimeoutError,
    ProcessingError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class SonarClient:
    """Async client for Perplexity Sonar API."""

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.perplexity_api_key
        self.model = settings.perplexity_model
        self.timeout = ClientTimeout(total=settings.request_timeout)

        # System prompt for fact-checking
        self.system_prompt = """You are a professional fact-checker with extensive research capabilities. Your task is to evaluate claims or articles for factual accuracy. Focus on identifying false, misleading, or unsubstantiated claims.

## Evaluation Process
For each piece of content, you will:
1. Identify specific claims that can be verified
2. Research each claim thoroughly using the most reliable sources available
3. Determine if each claim is:
   - TRUE: Factually accurate and supported by credible evidence
   - FALSE: Contradicted by credible evidence
   - MISLEADING: Contains some truth but presents information in a way that could lead to incorrect conclusions
   - UNVERIFIABLE: Cannot be conclusively verified with available information
4. For claims rated as FALSE or MISLEADING, explain why and provide corrections

## Guidelines
- Remain politically neutral and focus solely on factual accuracy
- Do not use political leaning as a factor in your evaluation
- Prioritize official data, peer-reviewed research, and reports from credible institutions
- Cite specific, reliable sources for your determinations
- Consider the context and intended meaning of statements
- Distinguish between factual claims and opinions
- Pay attention to dates, numbers, and specific details
- Be precise and thorough in your explanations"""

    async def research_claim(
        self,
        text: str,
        model: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Research a claim using Perplexity Sonar API.

        Args:
            text: The claim or article to research
            model: Optional model override
            custom_prompt: Optional custom system prompt

        Returns:
            Dictionary containing research results and citations

        Raises:
            PerplexityAPIError: When API call fails
            TimeoutError: When request times out
            ProcessingError: When response processing fails
        """
        if not text or not text.strip():
            raise ProcessingError("Cannot research empty text")

        model_to_use = model or self.model
        system_prompt = custom_prompt or self.system_prompt

        user_prompt = f"Research and fact-check the following claim or news article. Provide detailed analysis with sources:\n\n{text}"

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with ClientSession(timeout=self.timeout) as session:
                logger.info(
                    f"Sending research request to Perplexity Sonar with model: {model_to_use}"
                )

                async with session.post(
                    self.API_URL, headers=headers, json=data
                ) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        raise RateLimitError(
                            "Perplexity API rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None,
                        )

                    # Handle other HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            f"Perplexity API error {response.status}: {error_text}"
                        )
                        raise PerplexityAPIError(
                            f"Perplexity API request failed: {error_text}",
                            status_code=response.status,
                        )

                    result = await response.json()

                    # Extract content and citations
                    return self._process_response(result)

        except asyncio.TimeoutError:
            logger.error(
                f"Perplexity API request timed out after {self.settings.request_timeout}s"
            )
            raise TimeoutError(
                "Perplexity API request timed out",
                timeout_seconds=self.settings.request_timeout,
            )

        except aiohttp.ClientError as e:
            logger.error(f"Perplexity API client error: {str(e)}")
            raise PerplexityAPIError(f"API request failed: {str(e)}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Perplexity API response: {str(e)}")
            raise ProcessingError(f"Failed to parse API response: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in Perplexity API call: {str(e)}")
            raise ProcessingError(f"Unexpected error: {str(e)}")

    def _process_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the API response and extract relevant information.

        Args:
            result: Raw API response

        Returns:
            Processed response with content and citations

        Raises:
            ProcessingError: When response format is unexpected
        """
        try:
            # Extract citations
            citations = result.get("citations", [])

            # Extract content from choices
            if (
                "choices" in result
                and result["choices"]
                and "message" in result["choices"][0]
            ):
                content = result["choices"][0]["message"]["content"]

                return {
                    "content": content,
                    "citations": citations,
                    "model_used": result.get("model", self.model),
                    "usage": result.get("usage", {}),
                }

            # If no choices, return error
            raise ProcessingError("Unexpected API response format - no choices found")

        except KeyError as e:
            logger.error(f"Missing key in API response: {str(e)}")
            raise ProcessingError(f"Invalid API response format: missing {str(e)}")

        except Exception as e:
            logger.error(f"Error processing API response: {str(e)}")
            raise ProcessingError(f"Failed to process API response: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the Perplexity API is accessible.

        Returns:
            Dictionary with health status
        """
        try:
            # Use a simple test query
            test_result = await self.research_claim(
                "Test query: What is the capital of France?",
                model="sonar",  # Use basic model for health check
            )

            return {
                "status": "healthy",
                "response_time_ms": None,  # Could add timing here
                "model_available": True,
                "citations_available": len(test_result.get("citations", [])) > 0,
            }

        except Exception as e:
            logger.warning(f"Perplexity health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_available": False,
                "citations_available": False,
            }

    def get_available_models(self) -> List[str]:
        """
        Get list of available Perplexity models.

        Returns:
            List of model names
        """
        return ["sonar-pro", "sonar", "sonar-reasoning", "sonar-reasoning-pro"]
