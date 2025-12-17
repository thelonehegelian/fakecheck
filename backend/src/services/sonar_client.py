"""
Perplexity Sonar API client for fact-checking research using LangChain.
"""

import logging
from typing import Dict, Any, Optional, List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from src.core.config import Settings
from src.core.exceptions import (
    PerplexityAPIError,
    TimeoutError,
    ProcessingError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class SonarClient:
    """Async client for Perplexity Sonar API using LangChain (via ChatOpenAI)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.perplexity_api_key
        self.model = settings.perplexity_model
        self.timeout = settings.request_timeout

        # Initialize ChatOpenAI pointing to Perplexity
        # Perplexity provides an OpenAI-compatible API
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url="https://api.perplexity.ai",
            timeout=self.timeout,
            temperature=0,
            max_retries=2,
        )

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
        Research a claim using Perplexity Sonar API via LangChain.

        Args:
            text: The claim or article to research
            model: Optional model override
            custom_prompt: Optional custom system prompt

        Returns:
            Dictionary containing research results and citations
        """
        if not text or not text.strip():
            raise ProcessingError("Cannot research empty text")

        model_to_use = model or self.model
        
        # If model override is requested, we might need a new client instance or 
        # just pass it if supported (ChatOpenAI doesn't easily support per-request model override 
        # without creating a new instance or using configurable fields, but creating a new instance is safer/easier here)
        llm = self.llm
        if model and model != self.model:
             llm = ChatOpenAI(
                model=model,
                api_key=self.api_key,
                base_url="https://api.perplexity.ai",
                timeout=self.timeout,
                temperature=0,
                max_retries=2,
            )

        system_prompt = custom_prompt or self.system_prompt
        user_prompt = f"Research and fact-check the following claim or news article. Provide detailed analysis with sources:\n\n{text}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            logger.info(
                f"Sending research request to Perplexity Sonar (LangChain) with model: {model_to_use}"
            )

            # Invoke
            response = await llm.ainvoke(messages)
            
            # Extract content and citations
            # Perplexity via OpenAI compatible API returns citations in 'citations' field of the response object 
            # if using their specific client, but via LangChain's ChatOpenAI, it might be in response_metadata
            
            citations = []
            if response.response_metadata and "citations" in response.response_metadata:
                 citations = response.response_metadata["citations"]
            # Sometimes it might be in 'system_fingerprint' or other fields depending on how LangChain maps it,
            # but usually OpenAI compatible endpoints put extra stuff in response_metadata.
            
            # Fallback: Perplexity sometimes puts citations in the `citations` key of the raw return.
            # LangChain `response.response_metadata` usually captures the full raw response body or headers.
            
            return {
                "content": response.content,
                "citations": citations,
                "model_used": response.response_metadata.get("model", model_to_use),
                "usage": response.response_metadata.get("token_usage", {}),
            }

        except Exception as e:
            self._handle_langchain_exception(e)

    def _handle_langchain_exception(self, e: Exception) -> None:
        """
        Handle LangChain exceptions and map to application exceptions.
        """
        error_msg = str(e)
        logger.error(f"LangChain/Perplexity error: {error_msg}")
        
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
             raise RateLimitError("Perplexity API rate limit exceeded")
        
        if "timeout" in error_msg.lower():
            raise TimeoutError(
                "Perplexity API request timed out",
                timeout_seconds=self.settings.request_timeout,
            )
            
        if "api_error" in error_msg.lower() or "400" in error_msg:
             raise PerplexityAPIError(f"Perplexity API request failed: {error_msg}")

        # Fallback
        raise ProcessingError(f"Unexpected error: {error_msg}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the Perplexity API is accessible.

        Returns:
            Dictionary with health status
        """
        try:
            # Use a simple test query
            # We use the 'sonar' model (or whatever is default/configured) for a quick check
            # For health check, we want a very simple query
            messages = [HumanMessage(content="Test query: What is the capital of France? Short answer.")]
            
            # Use basic model for health check if possible to save credits? 
            # But we should test the configured one.
            response = await self.llm.ainvoke(messages)
            
            citations = []
            if response.response_metadata and "citations" in response.response_metadata:
                 citations = response.response_metadata["citations"]

            return {
                "status": "healthy",
                "response_time_ms": None,
                "model_available": True,
                "citations_available": True, # Assumed if call succeeds, though actual citations depend on query
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
