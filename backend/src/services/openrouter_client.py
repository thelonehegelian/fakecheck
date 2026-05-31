"""
OpenRouter API client for fact-checking operations.
Unified access to models with structured JSON parsing.
"""

import json
import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, NoReturn

from openrouter import OpenRouter
from pydantic import BaseModel, Field

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
    SourceCredibility,
    ExtractedClaim,
)

logger = logging.getLogger(__name__)


class ExtractClaimsTool(BaseModel):
    claims: List[ExtractedClaim] = Field(..., description="List of extracted claims")
    summary: str = Field(..., description="Extraction summary")


class VerifiabilityAnalysis(BaseModel):
    verification_methods: List[str] = Field(..., description="Methods to verify the claim")
    potential_sources: List[str] = Field(..., description="Sources that could verify the claim")
    difficulty_level: str = Field(..., description="Difficulty of verification")
    time_estimate: str = Field(..., description="Time estimate for verification")
    key_terms: List[str] = Field(..., description="Key terms for research")
    searchability_score: float = Field(..., description="How searchable is this claim")


def _call_openrouter(api_key: str, model: str, messages: List[Dict[str, str]], timeout: int) -> Any:
    """
    Synchronous function to call the OpenRouter SDK.
    Runs inside a thread pool via asyncio.to_thread.
    """
    with OpenRouter(api_key=api_key) as client:
        return client.chat.send(
            model=model,
            messages=messages,
            temperature=0,  # Deterministic for fact checking
        )


class OpenRouterClient:
    """Async client for OpenRouter API using native OpenRouter Python SDK and JSON parsing."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.timeout = settings.request_timeout

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required when using OpenRouter provider")

    def _parse_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Robustly extract and parse a JSON object from raw model output.
        Handles markdown blocks, prefix/suffix text, and raw JSON.
        """
        text = text.strip()
        
        # 1. Try to find a JSON block enclosed in markdown (```json ... ```)
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        # 2. Try parsing the whole text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 3. Strip any text before the first '{' and after the last '}'
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace+1])
            except json.JSONDecodeError:
                pass
                
        raise ValueError(f"Failed to parse a valid JSON object from response: {text[:200]}...")

    async def _send_chat_completion(self, system_prompt: str, user_content: str) -> str:
        """Helper to send chat completion with OpenRouter SDK in a non-blocking way."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        try:
            logger.info("Sending chat request to OpenRouter using model: %s", self.model)
            response = await asyncio.to_thread(
                _call_openrouter,
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                timeout=self.timeout
            )
            
            if not response or not response.choices:
                raise ExternalAPIError("Empty response or choices from OpenRouter API", service="openrouter")
                
            content = response.choices[0].message.content
            if not content:
                raise ExternalAPIError("Empty content in response choice from OpenRouter API", service="openrouter")
                
            return content
            
        except Exception as e:
            self._handle_exception(e)
            raise

    def _handle_exception(self, e: Exception) -> NoReturn:
        """Handle exceptions and map to application exceptions."""
        error_msg = str(e)
        logger.error("OpenRouter error: %s", error_msg)

        if "429" in error_msg or "rate limit" in error_msg.lower():
            raise RateLimitError("OpenRouter API rate limit exceeded")
        elif "timeout" in error_msg.lower():
            raise TimeoutError("OpenRouter API request timed out", timeout_seconds=self.timeout)
        elif isinstance(e, ExternalAPIError):
            raise e
        else:
            raise ExternalAPIError(f"OpenRouter API request failed: {error_msg}", service="openrouter")

    async def analyze_news(
        self,
        news_text: str,
        research_context: str,
        citations: List[str],
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze news content using OpenRouter API.
        """
        base_prompt = custom_prompt or self.settings.get_base_prompt()
        
        format_instructions = """
YOU MUST RESPOND ONLY WITH A VALID JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, CHAT, OR MARKDOWN BLOCK OUTSIDE THE JSON.
The JSON object must match this schema:
{
    "fake_news_rating": 1-5 (where 5 is definitely fake),
    "fake_news_explanation": "Explanation of why the news might be fake, including statistics and facts",
    "true_news_explanation": "Explanation of why the news might be true, including statistics and facts",
    "verification_steps": [
        {
            "step": "Description of the verification step",
            "estimated_time": "Estimated time to complete this step",
            "complexity": "easy", "medium", or "complex"
        }
    ],
    "confidence_score": 0.0-1.0 (estimated confidence score of the analysis),
    "confidence_interval": {
        "lower_bound": 0.0-1.0,
        "upper_bound": 0.0-1.0
    },
    "risk_factors": ["risk factor 1", "risk factor 2"]
}
"""
        system_prompt = f"{base_prompt}\n\n{format_instructions}"
        user_content = f"News to analyze: {news_text}\n\nResearch context: {research_context}\n\nCitations: {json.dumps(citations)}"

        content = await self._send_chat_completion(system_prompt, user_content)
        
        try:
            parsed_dict = self._parse_json_from_text(content)
            # Validate with Pydantic model to guarantee correct structure
            result = FactCheckResponse.model_validate(parsed_dict)
            
            response_dict = result.model_dump(exclude={"timestamp", "citations"})
            response_dict["model_used"] = self.model
            if citations:
                response_dict["citations"] = citations
                
            return response_dict
        except Exception as e:
            logger.error("Failed to parse/validate FactCheckResponse: %s", str(e))
            raise ProcessingError(f"Failed to process LLM response: {str(e)}")

    async def analyze_source_credibility(
        self, prompt: str, source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze source credibility using OpenRouter API.
        """
        format_instructions = """
YOU MUST RESPOND ONLY WITH A VALID JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, CHAT, OR MARKDOWN BLOCK OUTSIDE THE JSON.
The JSON object must match this schema:
{
    "domain": "Optional source domain (e.g. bbc.com)",
    "name": "Optional source name (e.g. BBC News)",
    "credibility_score": 0.0-100.0 (credibility score from 0-100),
    "bias_rating": "left", "center-left", "center", "center-right", "right", or "unknown",
    "factual_accuracy": "very-high", "high", "mostly-factual", "mixed", "low", "very-low", or "unknown",
    "transparency_score": 0.0-100.0 (transparency score from 0-100)
}
"""
        system_prompt = f"You are a media literacy expert analyzing news source credibility.\n\n{format_instructions}"
        user_content = f"{prompt}\n\nSource Info: {json.dumps(source_info)}"

        content = await self._send_chat_completion(system_prompt, user_content)
        
        try:
            parsed_dict = self._parse_json_from_text(content)
            result = SourceCredibility.model_validate(parsed_dict)
            
            response_dict = result.model_dump()
            response_dict["model_used"] = self.model
            return response_dict
        except Exception as e:
            logger.error("Failed to parse/validate SourceCredibility: %s", str(e))
            raise ProcessingError(f"Failed to process source credibility response: {str(e)}")

    async def extract_claims(
        self, prompt: str, text: str, extract_type: str = "factual", max_claims: int = 5
    ) -> Dict[str, Any]:
        """
        Extract claims from text using OpenRouter API.
        """
        format_instructions = f"""
YOU MUST RESPOND ONLY WITH A VALID JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, CHAT, OR MARKDOWN BLOCK OUTSIDE THE JSON.
Extract at most {max_claims} claims.
The JSON object must match this schema:
{{
    "claims": [
        {{
            "claim": "The extracted claim string",
            "claim_type": "factual", "opinion", "statistical", "prediction", or "other",
            "confidence": 0.0-1.0,
            "context": "Context surrounding the claim",
            "verifiable": true or false
        }}
    ],
    "summary": "Extraction summary string"
}}
"""
        system_prompt = f"You are an expert at extracting and analyzing claims from text content.\n\n{format_instructions}"
        user_content = f"{prompt}\n\nText: {text}\nExtract Type: {extract_type}"

        content = await self._send_chat_completion(system_prompt, user_content)
        
        try:
            parsed_dict = self._parse_json_from_text(content)
            result = ExtractClaimsTool.model_validate(parsed_dict)
            
            response_dict = {
                "claims": [c.model_dump() for c in result.claims],
                "summary": result.summary,
                "model_used": self.model
            }
            return response_dict
        except Exception as e:
            logger.error("Failed to parse/validate ClaimExtraction: %s", str(e))
            raise ProcessingError(f"Failed to process claim extraction response: {str(e)}")

    async def analyze_claim_verifiability(
        self, prompt: str, claim: str
    ) -> Dict[str, Any]:
        """
        Analyze how a claim can be verified using OpenRouter API.
        """
        format_instructions = """
YOU MUST RESPOND ONLY WITH A VALID JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT, CHAT, OR MARKDOWN BLOCK OUTSIDE THE JSON.
The JSON object must match this schema:
{
    "verification_methods": ["method 1", "method 2"],
    "potential_sources": ["source 1", "source 2"],
    "difficulty_level": "easy", "medium", or "complex",
    "time_estimate": "Estimated time to verify (e.g. 10 minutes)",
    "key_terms": ["term 1", "term 2"],
    "searchability_score": 0.0-1.0
}
"""
        system_prompt = f"You are an expert fact-checker analyzing how claims can be verified.\n\n{format_instructions}"
        user_content = f"{prompt}\n\nClaim to analyze: {claim}"

        content = await self._send_chat_completion(system_prompt, user_content)
        
        try:
            parsed_dict = self._parse_json_from_text(content)
            result = VerifiabilityAnalysis.model_validate(parsed_dict)
            
            response_dict = result.model_dump()
            response_dict["model_used"] = self.model
            return response_dict
        except Exception as e:
            logger.error("Failed to parse/validate VerifiabilityAnalysis: %s", str(e))
            raise ProcessingError(f"Failed to process verifiability analysis response: {str(e)}")

    async def extract_text_from_image(self, base64_image: str, mime_type: str) -> str:
        """
        Extract text from a base64-encoded image using OpenRouter multimodal vision.

        Args:
            base64_image: Raw base64 string (no prefix)
            mime_type: Mime type of the image (e.g. 'image/png')

        Returns:
            Extracted text content from the image
        """
        messages = [
            {
                "role": "system",
                "content": "You are an expert OCR and claim extraction system."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Please transcribe all readable text, claims, headings, or content in this image exactly as written. "
                            "Output ONLY the transcribed text. Do not include any commentary, intro, explanation, or markdown wrapper. "
                            "If there is no text in the image, reply with an empty response."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        try:
            logger.info("Sending vision-based OCR request to OpenRouter using model: %s", self.model)
            response = await asyncio.to_thread(
                _call_openrouter,
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                timeout=self.timeout
            )

            if not response or not response.choices:
                raise ExternalAPIError("Empty response or choices from OpenRouter API", service="openrouter")

            content = response.choices[0].message.content
            if not content:
                return ""

            return content.strip()

        except Exception as e:
            self._handle_exception(e)
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the OpenRouter API is accessible by running a fast prompt.
        """
        import time
        start_time = time.time()
        try:
            messages = [{"role": "user", "content": "respond only with 'OK'"}]
            
            response = await asyncio.to_thread(
                _call_openrouter,
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                timeout=10
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if response and response.choices and response.choices[0].message.content:
                return {
                    "status": "healthy",
                    "response_time_ms": response_time_ms,
                    "model_available": True,
                    "structured_output_available": True,
                }
            raise ValueError("No response content from OpenRouter during health check")
        except Exception as e:
            logger.warning("OpenRouter health check failed: %s", str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_available": False,
                "structured_output_available": False,
            }

    def get_available_models(self) -> List[str]:
        """
        Get list of configured/available OpenRouter models.
        """
        return [
            "google/gemini-3.5-flash",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "meta-llama/llama-3.3-70b-instruct",
        ]

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation).
        """
        return len(text) // 4
