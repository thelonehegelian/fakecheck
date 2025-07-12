"""
Main fact-checking service that orchestrates research and analysis.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from src.core.config import Settings
from src.core.exceptions import (
    ProcessingError,
    ValidationError,
    TimeoutError,
    ExternalAPIError,
)
from src.services.sonar_client import SonarClient
from src.services.anthropic_client import AnthropicClient
from src.models.requests import FactCheckRequest
from src.models.responses import FactCheckResponse

logger = logging.getLogger(__name__)


class FactCheckService:
    """Main service for fact-checking operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sonar_client = SonarClient(settings)
        self.anthropic_client = AnthropicClient(settings)

    async def check_news(self, request: FactCheckRequest) -> Dict[str, Any]:
        """
        Perform complete fact-checking analysis.

        Args:
            request: Fact-checking request

        Returns:
            Fact-checking results

        Raises:
            ValidationError: When input validation fails
            ProcessingError: When processing fails
            TimeoutError: When operation times out
            ExternalAPIError: When external API calls fail
        """
        start_time = time.time()

        try:
            logger.info(f"Starting fact-check for news: {request.news[:100]}...")

            # Step 1: Research the claim using Perplexity Sonar
            logger.info("Step 1: Researching claim with Perplexity Sonar")
            research_result = await self._research_claim(request)

            # Step 2: Analyze the news using Anthropic Claude
            logger.info("Step 2: Analyzing news with Anthropic Claude")
            analysis_result = await self._analyze_news(request, research_result)

            # Step 3: Add metadata
            processing_time = int((time.time() - start_time) * 1000)
            final_result = self._finalize_result(analysis_result, processing_time)

            logger.info(f"Fact-check completed in {processing_time}ms")
            return final_result

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Fact-check failed after {processing_time}ms: {str(e)}")
            raise

    async def _research_claim(self, request: FactCheckRequest) -> Dict[str, Any]:
        """
        Research the claim using Perplexity Sonar.

        Args:
            request: Fact-checking request

        Returns:
            Research results

        Raises:
            ExternalAPIError: When Sonar API fails
        """
        try:
            # Use custom prompt if provided, otherwise use default
            custom_prompt = None
            if request.custom_prompt:
                custom_prompt = request.custom_prompt

            research_result = await self.sonar_client.research_claim(
                text=request.news, custom_prompt=custom_prompt
            )

            logger.info(
                f"Research completed. Found {len(research_result.get('citations', []))} citations"
            )
            return research_result

        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            # Return minimal research result if API fails
            return {
                "content": f"Research failed: {str(e)}",
                "citations": [],
                "error": str(e),
            }

    async def _analyze_news(
        self, request: FactCheckRequest, research_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze the news using Anthropic Claude.

        Args:
            request: Fact-checking request
            research_result: Research results from Sonar

        Returns:
            Analysis results

        Raises:
            ExternalAPIError: When Anthropic API fails
        """
        try:
            research_context = research_result.get("content", "")
            citations = research_result.get("citations", [])

            # If research failed, note it in the context
            if "error" in research_result:
                research_context += f"\n\nNote: Research API failed with error: {research_result['error']}"

            analysis_result = await self.anthropic_client.analyze_news(
                news_text=request.news,
                research_context=research_context,
                citations=citations,
                custom_prompt=request.custom_prompt,
            )

            logger.info(
                f"Analysis completed. Rating: {analysis_result.get('fake_news_rating', 'N/A')}"
            )
            return analysis_result

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise ProcessingError(f"Analysis failed: {str(e)}")

    def _finalize_result(
        self, analysis_result: Dict[str, Any], processing_time: int
    ) -> Dict[str, Any]:
        """
        Finalize the result with additional metadata.

        Args:
            analysis_result: Analysis results
            processing_time: Processing time in milliseconds

        Returns:
            Finalized result
        """
        # Add processing metadata
        analysis_result["processing_time_ms"] = processing_time
        analysis_result["timestamp"] = datetime.utcnow().isoformat()

        # Calculate confidence score based on available data
        confidence_score = self._calculate_confidence_score(analysis_result)
        if confidence_score is not None:
            analysis_result["confidence_score"] = confidence_score

        return analysis_result

    def _calculate_confidence_score(
        self, analysis_result: Dict[str, Any]
    ) -> Optional[float]:
        """
        Calculate confidence score based on available data.

        Args:
            analysis_result: Analysis results

        Returns:
            Confidence score (0-1) or None if cannot be calculated
        """
        try:
            # Base confidence factors
            factors = []

            # Factor 1: Presence of citations
            citations = analysis_result.get("citations", [])
            if citations:
                citation_score = min(len(citations) / 5.0, 1.0)  # Max at 5 citations
                factors.append(citation_score * 0.3)  # 30% weight

            # Factor 2: Length and detail of explanations
            fake_explanation = analysis_result.get("fake_news_explanation", "")
            true_explanation = analysis_result.get("true_news_explanation", "")

            avg_explanation_length = (len(fake_explanation) + len(true_explanation)) / 2
            explanation_score = min(
                avg_explanation_length / 500.0, 1.0
            )  # Max at 500 chars
            factors.append(explanation_score * 0.2)  # 20% weight

            # Factor 3: Number of verification steps
            verification_steps = analysis_result.get("verification_steps", [])
            if verification_steps:
                steps_score = min(len(verification_steps) / 5.0, 1.0)  # Max at 5 steps
                factors.append(steps_score * 0.2)  # 20% weight

            # Factor 4: Rating extremity (more extreme ratings are generally more confident)
            rating = analysis_result.get("fake_news_rating", 3)
            rating_confidence = abs(rating - 3) / 2.0  # Distance from neutral (3)
            factors.append(rating_confidence * 0.3)  # 30% weight

            # Calculate weighted average
            if factors:
                return sum(factors) / len(factors)

            return None

        except Exception as e:
            logger.warning(f"Failed to calculate confidence score: {str(e)}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of all services.

        Returns:
            Dictionary with health status
        """
        results = {}

        # Check Sonar client
        try:
            sonar_health = await self.sonar_client.health_check()
            results["sonar"] = sonar_health
        except Exception as e:
            results["sonar"] = {"status": "unhealthy", "error": str(e)}

        # Check Anthropic client
        try:
            anthropic_health = await self.anthropic_client.health_check()
            results["anthropic"] = anthropic_health
        except Exception as e:
            results["anthropic"] = {"status": "unhealthy", "error": str(e)}

        # Overall health
        overall_healthy = all(
            service.get("status") == "healthy" for service in results.values()
        )

        results["overall"] = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "services_count": len(results) - 1,  # Exclude overall
            "healthy_services": sum(
                1 for service in results.values() if service.get("status") == "healthy"
            )
            - 1,  # Exclude overall
        }

        return results

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.

        Returns:
            Service information
        """
        return {
            "name": self.settings.app_name,
            "version": self.settings.app_version,
            "models": {
                "anthropic": self.anthropic_client.get_available_models(),
                "perplexity": self.sonar_client.get_available_models(),
            },
            "current_models": {
                "anthropic": self.settings.anthropic_model,
                "perplexity": self.settings.perplexity_model,
            },
            "limits": {
                "max_tokens": self.settings.max_tokens,
                "request_timeout": self.settings.request_timeout,
                "max_content_length": 10000,  # From request validation
            },
        }
