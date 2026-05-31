"""
Groq API client for fact-checking operations using LangChain.
Fast inference with Llama models.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

from src.core.config import Settings
from src.core.exceptions import (
    ExternalAPIError,
    ProcessingError,
    RateLimitError,
    TimeoutError,
)

# Import existing response models for structured output
from src.models.responses import (
    FactCheckResponse,
    SourceCredibilityResponse,
    ClaimExtractionResponse,
    VerificationStep,
    SourceCredibility,
    ExtractedClaim,
)

# Pydantic for custom structured output schemas
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GroqClient:
    """Async client for Groq API using LangChain."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.max_tokens = settings.max_tokens
        self.timeout = settings.request_timeout

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required when using Groq provider")

        # Initialize ChatGroq
        self.llm = ChatGroq(
            model_name=self.model,
            api_key=self.api_key,
            max_tokens=self.max_tokens,
            temperature=0,  # Deterministic for fact checking
            request_timeout=self.timeout,
            max_retries=2,
        )

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """
        Normalize problematic Unicode characters that break JSON schema validation.

        Args:
            text: Text with potentially problematic Unicode characters

        Returns:
            Normalized text with safe ASCII equivalents
        """
        if not text:
            return text

        # Replace narrow no-break space (\u202f) with regular space
        text = text.replace('\u202f', ' ')

        # Replace en-dash (–) and em-dash (—) with regular hyphen
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace('\u2013', '-').replace('\u2014', '-')

        # Replace en-dash variant (\u2011) with hyphen
        text = text.replace('\u2011', '-')

        # Replace curly quotes with straight quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")

        # Replace ellipsis character with three dots
        text = text.replace('…', '...')
        text = text.replace('\u2026', '...')

        return text

    def _normalize_dict_unicode(self, data: Any) -> Any:
        """
        Recursively normalize Unicode characters in dictionaries and lists.
        Also fixes schema validation issues (e.g., bias_rating values).

        Args:
            data: Dictionary, list, or string to normalize

        Returns:
            Normalized data structure
        """
        if isinstance(data, str):
            return self._normalize_unicode(data)
        elif isinstance(data, dict):
            normalized = {}
            for key, value in data.items():
                # Fix bias_rating field - convert invalid values to "unknown"
                if key == "bias_rating" and isinstance(value, str):
                    valid_bias_values = ["left", "center-left", "center", "center-right", "right", "unknown"]
                    if value.lower() not in valid_bias_values:
                        logger.warning(f"Invalid bias_rating '{value}', converting to 'unknown'")
                        normalized[key] = "unknown"
                    else:
                        normalized[key] = value
                else:
                    normalized[key] = self._normalize_dict_unicode(value)
            return normalized
        elif isinstance(data, list):
            return [self._normalize_dict_unicode(item) for item in data]
        else:
            return data

    async def analyze_news(
        self,
        news_text: str,
        research_context: str,
        citations: List[str],
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze news content using Groq API via LangChain.

        Args:
            news_text: The news content to analyze
            research_context: Context from research
            citations: List of citations
            custom_prompt: Custom system prompt

        Returns:
            Dictionary with analysis results matching FactCheckResponse structure
        """
        # Get system prompt
        system_prompt = custom_prompt or self.settings.get_base_prompt()

        # Define the prompt template
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "human",
                    """News to analyze: {news_text}

Research context: {research_context}

Citations: {citations}""",
                ),
            ]
        )

        # Configure structured output using the Pydantic model
        structured_llm = self.llm.with_structured_output(FactCheckResponse)

        chain = prompt_template | structured_llm

        try:
            logger.info(
                f"Sending analysis request to Groq (LangChain) with model: {self.model}"
            )

            # Invoke the chain
            result: FactCheckResponse = await chain.ainvoke(
                {
                    "system_prompt": system_prompt,
                    "news_text": news_text,
                    "research_context": research_context,
                    "citations": json.dumps(citations),
                }
            )

            # Convert Pydantic model to dict for compatibility with existing code
            response_dict = result.model_dump(exclude={"timestamp", "citations"})

            # Normalize Unicode characters that break JSON schema validation
            response_dict = self._normalize_dict_unicode(response_dict)

            # Fix: Ensure fake_news_rating is an integer (Groq sometimes returns string)
            if "fake_news_rating" in response_dict and isinstance(response_dict["fake_news_rating"], str):
                try:
                    response_dict["fake_news_rating"] = int(response_dict["fake_news_rating"])
                except ValueError:
                    logger.warning(f"Could not convert rating to int: {response_dict['fake_news_rating']}")
                    response_dict["fake_news_rating"] = 3  # Default to middle rating

            # Add metadata
            response_dict["model_used"] = self.model

            # Ensure citations are included
            if citations:
                response_dict["citations"] = citations

            return response_dict

        except ExternalAPIError as e:
            # Check if we extracted data from failed_generation
            if hasattr(e, 'extracted_data') and e.extracted_data:
                logger.warning("Using extracted data from failed Groq validation")
                response_dict = e.extracted_data

                # Fix fake_news_rating type
                if "fake_news_rating" in response_dict and isinstance(response_dict["fake_news_rating"], str):
                    try:
                        response_dict["fake_news_rating"] = int(response_dict["fake_news_rating"])
                    except ValueError:
                        logger.warning(f"Could not convert rating to int: {response_dict['fake_news_rating']}")
                        response_dict["fake_news_rating"] = 3

                # Add metadata
                response_dict["model_used"] = self.model

                # Ensure citations are included
                if citations:
                    response_dict["citations"] = citations

                return response_dict
            else:
                raise
        except Exception as e:
            self._handle_langchain_exception(e)

    async def analyze_source_credibility(
        self, prompt: str, source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze source credibility using Groq API via LangChain.

        Args:
            prompt: Analysis prompt
            source_info: Source information

        Returns:
            Dictionary with credibility analysis results
        """
        # Define the prompt template
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a media literacy expert analyzing news source credibility.",
                ),
                ("human", "{prompt}"),
            ]
        )

        # Use the SourceCredibility model for structured output
        structured_llm = self.llm.with_structured_output(SourceCredibility)
        chain = prompt_template | structured_llm

        try:
            logger.info("Sending source analysis request to Groq (LangChain)")
            result: SourceCredibility = await chain.ainvoke({"prompt": prompt})

            response_dict = result.model_dump()
            response_dict = self._normalize_dict_unicode(response_dict)
            response_dict["model_used"] = self.model
            return response_dict

        except Exception as e:
            self._handle_langchain_exception(e)

    async def extract_claims(
        self, prompt: str, text: str, extract_type: str = "factual", max_claims: int = 5
    ) -> Dict[str, Any]:
        """
        Extract claims from text using Groq API via LangChain.

        Args:
            prompt: Extraction prompt
            text: Text to extract claims from
            extract_type: Type of claims to extract
            max_claims: Maximum number of claims

        Returns:
            Dictionary with extracted claims
        """
        # Define the prompt template
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert at extracting and analyzing claims from text content.",
                ),
                ("human", "{prompt}"),
            ]
        )

        class ExtractClaimsTool(BaseModel):
            claims: List[ExtractedClaim] = Field(..., description="List of extracted claims")
            summary: str = Field(..., description="Extraction summary")

        structured_llm = self.llm.with_structured_output(ExtractClaimsTool)
        chain = prompt_template | structured_llm

        try:
            logger.info("Sending claim extraction request to Groq (LangChain)")
            result = await chain.ainvoke({"prompt": prompt})

            response_dict = {
                "claims": [c.model_dump() for c in result.claims],
                "summary": result.summary,
                "model_used": self.model
            }
            response_dict = self._normalize_dict_unicode(response_dict)
            return response_dict

        except Exception as e:
            self._handle_langchain_exception(e)

    async def analyze_claim_verifiability(
        self, prompt: str, claim: str
    ) -> Dict[str, Any]:
        """
        Analyze how a claim can be verified using Groq API via LangChain.

        Args:
            prompt: Analysis prompt
            claim: Claim to analyze

        Returns:
            Dictionary with verifiability analysis

        Raises:
            ExternalAPIError: When API call fails
            ProcessingError: When response processing fails
        """
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert fact-checker analyzing how claims can be verified.",
                ),
                ("human", "{prompt}"),
            ]
        )

        # Define schema for verifiability
        class VerifiabilityAnalysis(BaseModel):
            verification_methods: List[str] = Field(..., description="Methods to verify the claim")
            potential_sources: List[str] = Field(..., description="Sources that could verify the claim")
            difficulty_level: str = Field(..., description="Difficulty of verification")
            time_estimate: str = Field(..., description="Time estimate for verification")
            key_terms: List[str] = Field(..., description="Key terms for research")
            searchability_score: float = Field(..., description="How searchable is this claim")

        structured_llm = self.llm.with_structured_output(VerifiabilityAnalysis)
        chain = prompt_template | structured_llm

        try:
            logger.info("Sending verifiability analysis request to Groq (LangChain)")
            result = await chain.ainvoke({"prompt": prompt})

            response_dict = result.model_dump()
            response_dict = self._normalize_dict_unicode(response_dict)
            response_dict["model_used"] = self.model
            return response_dict

        except Exception as e:
            self._handle_langchain_exception(e)

    def _extract_failed_generation(self, error_msg: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse the failed_generation field from Groq error messages.

        Args:
            error_msg: Error message from Groq

        Returns:
            Parsed JSON from failed_generation, or None if not found or unusable
        """
        try:
            # Look for failed_generation in the error message
            if "failed_generation" not in error_msg:
                logger.debug("No failed_generation field found in error message")
                return None

            # Extract the JSON - it's after 'failed_generation': '...'
            start_markers = ["'failed_generation': '", '"failed_generation": "']
            json_str = None

            for marker in start_markers:
                if marker in error_msg:
                    start_idx = error_msg.find(marker) + len(marker)
                    # Find the matching closing quote (handle escaped quotes)
                    end_idx = start_idx
                    escape_count = 0
                    while end_idx < len(error_msg):
                        if error_msg[end_idx] == '\\':
                            escape_count += 1
                        elif error_msg[end_idx] in ['"', "'"] and escape_count % 2 == 0:
                            json_str = error_msg[start_idx:end_idx]
                            break
                        else:
                            escape_count = 0
                        end_idx += 1
                    if json_str:
                        break

            if not json_str:
                logger.debug("Could not extract JSON string from failed_generation")
                return None

            # Clean up escaped characters
            json_str = json_str.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")

            # Parse the outer JSON (tool call format) using raw_decode to handle extra data
            from json import JSONDecoder
            decoder = JSONDecoder()

            try:
                # Use raw_decode to parse JSON and ignore extra data after it
                tool_call, end_pos = decoder.raw_decode(json_str)

                # Extract just the arguments
                if isinstance(tool_call, dict) and "arguments" in tool_call:
                    parsed = tool_call["arguments"]
                else:
                    parsed = tool_call

                # Normalize Unicode characters
                parsed = self._normalize_dict_unicode(parsed)

                # Check if the extracted data is actually usable
                # Required fields: fake_news_rating and verification_steps
                if not parsed.get("fake_news_rating") or not parsed.get("verification_steps"):
                    logger.warning(
                        f"Extracted failed_generation has null/missing required fields: "
                        f"fake_news_rating={parsed.get('fake_news_rating')}, "
                        f"verification_steps={parsed.get('verification_steps')}"
                    )
                    return None

                logger.info("Successfully extracted usable data from failed_generation")
                return parsed

            except json.JSONDecodeError as e:
                logger.debug(f"JSON decode error: {str(e)}, trying alternative parsing")
                # If raw_decode fails, the JSON might be incomplete or malformed
                # Return None to fall back to raising the original error
                return None

        except Exception as ex:
            logger.warning(f"Failed to extract failed_generation: {str(ex)}")
            return None

    def _handle_langchain_exception(self, e: Exception) -> None:
        """
        Handle LangChain exceptions and map to application exceptions.
        Attempts to extract failed_generation for tool_use_failed errors.
        """
        error_msg = str(e)
        logger.error(f"LangChain/Groq error: {error_msg}")

        # Check for rate limit
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise RateLimitError("Groq API rate limit exceeded")

        if "timeout" in error_msg.lower():
            raise TimeoutError(
                "Groq API request timed out",
                timeout_seconds=self.settings.request_timeout,
            )

        # Handle tool_use_failed with failed_generation extraction
        if "tool_use_failed" in error_msg.lower():
            failed_data = self._extract_failed_generation(error_msg)
            if failed_data:
                # Attach the extracted data to the exception
                error = ExternalAPIError(
                    f"Groq tool validation failed, but response was extracted",
                    service="groq"
                )
                error.extracted_data = failed_data
                raise error

            raise ExternalAPIError(f"Groq API request failed: {error_msg}", service="groq")

        # Generic API errors
        if "api_error" in error_msg.lower() or "400" in error_msg:
            raise ExternalAPIError(f"Groq API request failed: {error_msg}", service="groq")

        # Processing/Validation errors
        if isinstance(e, OutputParserException):
            raise ProcessingError(f"Failed to parse API response: {error_msg}")

        # Fallback
        raise ProcessingError(f"Unexpected error: {error_msg}")

    async def extract_text_from_image(self, base64_image: str, mime_type: str) -> str:
        """
        Extract text from a base64-encoded image (Stub, vision not supported on Groq).
        """
        raise ProcessingError("Groq client does not currently support image OCR. Please use OpenRouter or Anthropic providers for image fact-checking.")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the Groq API is accessible.

        Returns:
            Dictionary with health status
        """
        try:
            # Simple invocation
            prompt = ChatPromptTemplate.from_template("Hello, respond with 'OK'")
            chain = prompt | self.llm
            result = await chain.ainvoke({})

            return {
                "status": "healthy",
                "response_time_ms": None,
                "model_available": True,
                "structured_output_available": True,
            }

        except Exception as e:
            logger.warning(f"Groq health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_available": False,
                "structured_output_available": False,
            }

    def get_available_models(self) -> List[str]:
        """
        Get list of available Groq models.

        Returns:
            List of model names
        """
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
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
