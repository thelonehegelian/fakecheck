"""
Source credibility analysis service.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from src.core.config import Settings
from src.core.exceptions import ProcessingError, ValidationError
from src.services.llm_factory import LLMFactory
from src.models.responses import SourceCredibility

logger = logging.getLogger(__name__)


class SourceCredibilityService:
    """Service for analyzing source credibility."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_client = LLMFactory.create_client(settings)

        # Known source database (in production, this would be a real database)
        self.known_sources = {
            "bbc.com": {
                "name": "BBC News",
                "credibility_score": 85.5,
                "bias_rating": "center-left",
                "factual_accuracy": "high",
                "transparency_score": 92.0,
            },
            "reuters.com": {
                "name": "Reuters",
                "credibility_score": 88.0,
                "bias_rating": "center",
                "factual_accuracy": "very-high",
                "transparency_score": 95.0,
            },
            "cnn.com": {
                "name": "CNN",
                "credibility_score": 72.0,
                "bias_rating": "left",
                "factual_accuracy": "mostly-factual",
                "transparency_score": 78.0,
            },
            "foxnews.com": {
                "name": "Fox News",
                "credibility_score": 65.0,
                "bias_rating": "right",
                "factual_accuracy": "mixed",
                "transparency_score": 70.0,
            },
            "apnews.com": {
                "name": "Associated Press",
                "credibility_score": 90.0,
                "bias_rating": "center",
                "factual_accuracy": "very-high",
                "transparency_score": 96.0,
            },
            "nytimes.com": {
                "name": "The New York Times",
                "credibility_score": 82.0,
                "bias_rating": "center-left",
                "factual_accuracy": "high",
                "transparency_score": 88.0,
            },
            "washingtonpost.com": {
                "name": "The Washington Post",
                "credibility_score": 80.0,
                "bias_rating": "center-left",
                "factual_accuracy": "high",
                "transparency_score": 86.0,
            },
            "wsj.com": {
                "name": "The Wall Street Journal",
                "credibility_score": 84.0,
                "bias_rating": "center-right",
                "factual_accuracy": "high",
                "transparency_score": 90.0,
            },
            "npr.org": {
                "name": "NPR",
                "credibility_score": 87.0,
                "bias_rating": "center-left",
                "factual_accuracy": "high",
                "transparency_score": 93.0,
            },
            "theguardian.com": {
                "name": "The Guardian",
                "credibility_score": 78.0,
                "bias_rating": "center-left",
                "factual_accuracy": "mostly-factual",
                "transparency_score": 85.0,
            },
        }

    async def analyze_source_credibility(
        self,
        source_url: Optional[str] = None,
        source_domain: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> SourceCredibility:
        """
        Analyze the credibility of a news source.

        Args:
            source_url: URL of the source
            source_domain: Domain of the source
            source_name: Name of the source

        Returns:
            SourceCredibility object with analysis results

        Raises:
            ValidationError: When input validation fails
            ProcessingError: When analysis fails
        """
        try:
            # Extract domain from URL if provided
            if source_url and not source_domain:
                parsed_url = urlparse(source_url)
                source_domain = parsed_url.netloc.lower()
                # Remove www. prefix
                if source_domain.startswith("www."):
                    source_domain = source_domain[4:]

            if not source_domain and not source_name:
                raise ValidationError(
                    "Either source_domain or source_name must be provided"
                )

            logger.info(
                f"Analyzing credibility for domain: {source_domain}, name: {source_name}"
            )

            # Check if source is in known database
            if source_domain and source_domain in self.known_sources:
                known_data = self.known_sources[source_domain]
                return SourceCredibility(
                    domain=source_domain,
                    name=known_data["name"],
                    credibility_score=known_data["credibility_score"],
                    bias_rating=known_data["bias_rating"],
                    factual_accuracy=known_data["factual_accuracy"],
                    transparency_score=known_data.get("transparency_score"),
                )

            # For unknown sources, use AI analysis
            return await self._analyze_unknown_source(
                source_url, source_domain, source_name
            )

        except Exception as e:
            logger.error(f"Source credibility analysis failed: {str(e)}")
            raise ProcessingError(f"Failed to analyze source credibility: {str(e)}")

    async def _analyze_unknown_source(
        self,
        source_url: Optional[str],
        source_domain: Optional[str],
        source_name: Optional[str],
    ) -> SourceCredibility:
        """
        Analyze unknown source using AI.

        Args:
            source_url: URL of the source
            source_domain: Domain of the source
            source_name: Name of the source

        Returns:
            SourceCredibility object with AI analysis results
        """
        try:
            # Create analysis prompt
            prompt = self._create_source_analysis_prompt(
                source_url, source_domain, source_name
            )

            # Use Anthropic for analysis
            analysis_result = await self.llm_client.analyze_source_credibility(
                prompt=prompt,
                source_info={
                    "url": source_url,
                    "domain": source_domain,
                    "name": source_name,
                },
            )

            # Parse AI results into SourceCredibility object
            return SourceCredibility(
                domain=source_domain,
                name=source_name or analysis_result.get("name"),
                credibility_score=analysis_result.get("credibility_score", 50.0),
                bias_rating=analysis_result.get("bias_rating", "unknown"),
                factual_accuracy=analysis_result.get("factual_accuracy", "unknown"),
                transparency_score=analysis_result.get("transparency_score", 50.0),
            )

        except Exception as e:
            logger.warning(f"AI analysis failed, using fallback: {str(e)}")
            # Return conservative estimate for unknown sources
            return SourceCredibility(
                domain=source_domain,
                name=source_name or "Unknown Source",
                credibility_score=50.0,
                bias_rating="unknown",
                factual_accuracy="unknown",
                transparency_score=50.0,
            )

    def _create_source_analysis_prompt(
        self,
        source_url: Optional[str],
        source_domain: Optional[str],
        source_name: Optional[str],
    ) -> str:
        """
        Create a prompt for source analysis.

        Args:
            source_url: URL of the source
            source_domain: Domain of the source
            source_name: Name of the source

        Returns:
            Analysis prompt string
        """
        prompt = f"""
        Please analyze the credibility of this news source:
        
        URL: {source_url or 'Not provided'}
        Domain: {source_domain or 'Not provided'}
        Name: {source_name or 'Not provided'}
        
        Please provide:
        1. Credibility score (0-100, where 100 is most credible)
        2. Political bias rating (left, center-left, center, center-right, right, or unknown)
        3. Factual accuracy rating (very-high, high, mostly-factual, mixed, low, very-low, or unknown)
        4. Transparency score (0-100, based on disclosure of ownership, funding, corrections policy)
        
        Consider factors like:
        - Journalistic standards and ethics
        - Fact-checking practices
        - Correction policies
        - Transparency about ownership and funding
        - Historical accuracy
        - Editorial independence
        - Peer recognition in journalism
        
        If you're not familiar with this source, please indicate that and provide conservative estimates.
        """
        return prompt

    async def get_source_recommendations(
        self, source_credibility: SourceCredibility
    ) -> List[str]:
        """
        Get recommendations for using a source based on its credibility.

        Args:
            source_credibility: SourceCredibility object

        Returns:
            List of recommendations
        """
        recommendations = []

        # Credibility-based recommendations
        if source_credibility.credibility_score >= 85:
            recommendations.append("Excellent source with high credibility")
            recommendations.append("Suitable for authoritative information")
        elif source_credibility.credibility_score >= 70:
            recommendations.append("Good source with decent credibility")
            recommendations.append(
                "Cross-reference with other sources for important claims"
            )
        elif source_credibility.credibility_score >= 50:
            recommendations.append("Moderate credibility - use with caution")
            recommendations.append("Always verify information with multiple sources")
        else:
            recommendations.append(
                "Low credibility - not recommended as primary source"
            )
            recommendations.append("Fact-check all claims from this source")

        # Bias-based recommendations
        if source_credibility.bias_rating in ["left", "right"]:
            recommendations.append(
                f"Consider {source_credibility.bias_rating}-leaning bias in editorial content"
            )
            recommendations.append("Seek opposing viewpoints for balanced perspective")
        elif source_credibility.bias_rating in ["center-left", "center-right"]:
            recommendations.append(
                f"Slight {source_credibility.bias_rating} bias - generally balanced"
            )

        # Factual accuracy recommendations
        if source_credibility.factual_accuracy in ["low", "very-low"]:
            recommendations.append("Poor factual accuracy - high verification needed")
        elif source_credibility.factual_accuracy == "mixed":
            recommendations.append("Mixed factual accuracy - verify key claims")

        return recommendations

    async def find_similar_sources(
        self, source_credibility: SourceCredibility, limit: int = 5
    ) -> List[SourceCredibility]:
        """
        Find similar sources based on credibility and bias.

        Args:
            source_credibility: SourceCredibility object to find similar sources for
            limit: Maximum number of similar sources to return

        Returns:
            List of similar SourceCredibility objects
        """
        similar_sources = []

        for domain, data in self.known_sources.items():
            # Skip if it's the same domain
            if domain == source_credibility.domain:
                continue

            # Calculate similarity score
            similarity_score = self._calculate_similarity(source_credibility, data)

            if similarity_score > 0.7:  # Threshold for similarity
                similar_source = SourceCredibility(
                    domain=domain,
                    name=data["name"],
                    credibility_score=data["credibility_score"],
                    bias_rating=data["bias_rating"],
                    factual_accuracy=data["factual_accuracy"],
                    transparency_score=data.get("transparency_score"),
                )
                similar_sources.append((similarity_score, similar_source))

        # Sort by similarity score and return top results
        similar_sources.sort(key=lambda x: x[0], reverse=True)
        return [source for _, source in similar_sources[:limit]]

    def _calculate_similarity(
        self, source_credibility: SourceCredibility, known_data: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity between two sources.

        Args:
            source_credibility: SourceCredibility object
            known_data: Known source data

        Returns:
            Similarity score (0-1)
        """
        similarity_factors = []

        # Credibility score similarity (weight: 40%)
        if source_credibility.credibility_score is not None:
            credibility_diff = abs(
                source_credibility.credibility_score - known_data["credibility_score"]
            )
            credibility_similarity = 1 - (credibility_diff / 100)
            similarity_factors.append(credibility_similarity * 0.4)

        # Bias rating similarity (weight: 30%)
        if (
            source_credibility.bias_rating
            and source_credibility.bias_rating != "unknown"
        ):
            bias_similarity = (
                1.0
                if source_credibility.bias_rating == known_data["bias_rating"]
                else 0.5
            )
            similarity_factors.append(bias_similarity * 0.3)

        # Factual accuracy similarity (weight: 30%)
        if (
            source_credibility.factual_accuracy
            and source_credibility.factual_accuracy != "unknown"
        ):
            accuracy_similarity = (
                1.0
                if source_credibility.factual_accuracy == known_data["factual_accuracy"]
                else 0.5
            )
            similarity_factors.append(accuracy_similarity * 0.3)

        return sum(similarity_factors) if similarity_factors else 0.0

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the source credibility service is healthy.

        Returns:
            Dictionary with health status
        """
        try:
            # Test basic functionality
            test_result = await self.analyze_source_credibility(source_domain="bbc.com")

            return {
                "status": "healthy",
                "known_sources_count": len(self.known_sources),
                "test_analysis_successful": test_result.credibility_score > 0,
            }
        except Exception as e:
            logger.warning(f"Source credibility health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
