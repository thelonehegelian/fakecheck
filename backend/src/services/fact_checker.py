"""
Main fact-checking service that orchestrates research and analysis.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import re

from src.core.config import Settings
from src.core.exceptions import (
    ProcessingError,
    ValidationError,
    TimeoutError,
    ExternalAPIError,
)
from src.services.sonar_client import SonarClient
from src.services.llm_factory import LLMFactory
from src.services.source_credibility import SourceCredibilityService
from src.services.claim_extraction import ClaimExtractionService
from src.models.requests import FactCheckRequest, BatchFactCheckRequest
from src.models.responses import FactCheckResponse, SourceCredibility, ExtractedClaim

logger = logging.getLogger(__name__)


class FactCheckService:
    """Main service for fact-checking operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sonar_client = SonarClient(settings)
        # Use factory to create the appropriate LLM client
        self.llm_client = LLMFactory.create_client(settings)
        self.source_credibility_service = SourceCredibilityService(settings)
        self.claim_extraction_service = ClaimExtractionService(settings)

    async def check_news(self, request: FactCheckRequest) -> Dict[str, Any]:
        """
        Perform complete fact-checking analysis with Phase 1 enhancements.

        Args:
            request: Fact-checking request

        Returns:
            Enhanced fact-checking results

        Raises:
            ValidationError: When input validation fails
            ProcessingError: When processing fails
            TimeoutError: When operation times out
            ExternalAPIError: When external API calls fail
        """
        start_time = time.time()

        try:
            logger.info(
                f"Starting enhanced fact-check for news: {request.news[:100]}..."
            )

            # Step 1: Research the claim using Perplexity Sonar
            logger.info("Step 1: Researching claim with Perplexity Sonar")
            research_result = await self._research_claim(request)

            # Step 2: Extract claims from the news content
            logger.info("Step 2: Extracting claims from content")
            extracted_claims = await self._extract_claims(request)

            # Step 3: Analyze source credibility from URLs in content
            logger.info("Step 3: Analyzing source credibility")
            source_analysis = await self._analyze_sources(request.news)

            # Step 4: Analyze the news using Anthropic Claude
            logger.info("Step 4: Analyzing news with Anthropic Claude")
            analysis_result = await self._analyze_news(request, research_result)

            # Step 5: Add Phase 1 enhancements
            logger.info("Step 5: Adding enhanced analysis")
            enhanced_result = await self._enhance_analysis(
                analysis_result, extracted_claims, source_analysis, research_result
            )

            # Step 6: Add metadata and finalize
            processing_time = int((time.time() - start_time) * 1000)
            final_result = self._finalize_result(enhanced_result, processing_time)

            logger.info(f"Enhanced fact-check completed in {processing_time}ms")
            return final_result

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(
                f"Enhanced fact-check failed after {processing_time}ms: {str(e)}"
            )
            raise

    async def check_news_batch(self, request: BatchFactCheckRequest) -> Dict[str, Any]:
        """
        Perform batch fact-checking analysis.

        Args:
            request: Batch fact-checking request

        Returns:
            Batch fact-checking results

        Raises:
            ValidationError: When input validation fails
            ProcessingError: When processing fails
        """
        start_time = time.time()

        try:
            logger.info(f"Starting batch fact-check for {len(request.items)} items")

            # Process items in parallel or sequentially based on settings
            parallel_processing = (
                request.batch_settings.get("parallel_processing", True)
                if request.batch_settings
                else True
            )

            if parallel_processing:
                # Process items in parallel (limited concurrency)
                semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests
                tasks = []

                for i, item in enumerate(request.items):
                    task = self._process_batch_item(semaphore, i, item)
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Process items sequentially
                results = []
                for i, item in enumerate(request.items):
                    result = await self._process_batch_item(None, i, item)
                    results.append(result)

            # Compile batch results
            successful_items = 0
            failed_items = 0
            processed_results = []

            for result in results:
                if isinstance(result, Exception):
                    failed_items += 1
                    processed_results.append(
                        {
                            "item_id": len(processed_results),
                            "status": "failed",
                            "error": str(result),
                        }
                    )
                else:
                    successful_items += 1
                    processed_results.append(result)

            # Calculate batch summary
            batch_summary = self._calculate_batch_summary(processed_results)

            processing_time = int((time.time() - start_time) * 1000)

            return {
                "total_items": len(request.items),
                "successful_items": successful_items,
                "failed_items": failed_items,
                "results": processed_results,
                "batch_summary": batch_summary,
                "processing_time_ms": processing_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Batch fact-check failed after {processing_time}ms: {str(e)}")
            raise ProcessingError(f"Batch processing failed: {str(e)}")

    async def _process_batch_item(
        self,
        semaphore: Optional[asyncio.Semaphore],
        item_id: int,
        item: FactCheckRequest,
    ) -> Dict[str, Any]:
        """
        Process a single item in a batch.

        Args:
            semaphore: Semaphore for controlling concurrency
            item_id: ID of the item
            item: Fact-checking request

        Returns:
            Processed item result
        """

        async def process_item():
            try:
                result = await self.check_news(item)
                return {"item_id": item_id, "status": "success", "result": result}
            except Exception as e:
                logger.error(f"Failed to process batch item {item_id}: {str(e)}")
                return {"item_id": item_id, "status": "failed", "error": str(e)}

        if semaphore:
            async with semaphore:
                return await process_item()
        else:
            return await process_item()

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

    async def _extract_claims(self, request: FactCheckRequest) -> List[ExtractedClaim]:
        """
        Extract claims from the news content.

        Args:
            request: Fact-checking request

        Returns:
            List of extracted claims
        """
        try:
            claims = await self.claim_extraction_service.extract_claims(
                text=request.news,
                extract_type="factual",
                max_claims=3,  # Limit to 3 most important claims
            )
            logger.info(f"Extracted {len(claims)} claims from content")
            return claims
        except Exception as e:
            logger.warning(f"Claim extraction failed: {str(e)}")
            return []

    async def _analyze_sources(self, news_text: str) -> List[SourceCredibility]:
        """
        Analyze source credibility from URLs mentioned in the news.

        Args:
            news_text: News content to analyze

        Returns:
            List of source credibility analyses
        """
        try:
            # Extract URLs from the news text
            urls = self._extract_urls(news_text)

            if not urls:
                return []

            # Analyze credibility for each unique domain
            domains = set()
            for url in urls:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    domains.add(domain)
                except:
                    continue

            # Limit to top 3 domains to avoid too many API calls
            domains = list(domains)[:3]

            source_analyses = []
            for domain in domains:
                try:
                    analysis = await self.source_credibility_service.analyze_source_credibility(
                        source_domain=domain
                    )
                    source_analyses.append(analysis)
                except Exception as e:
                    logger.warning(f"Failed to analyze source {domain}: {str(e)}")
                    continue

            logger.info(f"Analyzed credibility for {len(source_analyses)} sources")
            return source_analyses

        except Exception as e:
            logger.warning(f"Source analysis failed: {str(e)}")
            return []

    def _extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text.

        Args:
            text: Text to extract URLs from

        Returns:
            List of URLs found in the text
        """
        # Simple URL regex pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+|www\.[^\s<>"{}|\\^`[\]]+'
        urls = re.findall(url_pattern, text, re.IGNORECASE)

        # Clean up URLs
        cleaned_urls = []
        for url in urls:
            url = url.strip(".,;:!?")  # Remove trailing punctuation
            if not url.startswith("http"):
                url = "https://" + url
            cleaned_urls.append(url)

        return cleaned_urls

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

            analysis_result = await self.llm_client.analyze_news(
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

    async def _enhance_analysis(
        self,
        analysis_result: Dict[str, Any],
        extracted_claims: List[ExtractedClaim],
        source_analysis: List[SourceCredibility],
        research_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Add Phase 1 enhancements to the analysis.

        Args:
            analysis_result: Base analysis results
            extracted_claims: Extracted claims
            source_analysis: Source credibility analysis
            research_result: Research results

        Returns:
            Enhanced analysis results
        """
        # Add extracted claims
        if extracted_claims:
            analysis_result["extracted_claims"] = [
                {
                    "claim": claim.claim,
                    "claim_type": claim.claim_type,
                    "confidence": claim.confidence,
                    "verifiable": claim.verifiable,
                    "context": claim.context,
                }
                for claim in extracted_claims
            ]

        # Add source analysis
        if source_analysis:
            analysis_result["source_analysis"] = [
                {
                    "domain": source.domain,
                    "name": source.name,
                    "credibility_score": source.credibility_score,
                    "bias_rating": source.bias_rating,
                    "factual_accuracy": source.factual_accuracy,
                    "transparency_score": source.transparency_score,
                }
                for source in source_analysis
            ]

        # Calculate confidence interval
        confidence_score = analysis_result.get("confidence_score")
        if confidence_score is None:
            confidence_score = 0.5
            
        confidence_interval = self._calculate_confidence_interval(
            confidence_score, analysis_result, source_analysis
        )
        analysis_result["confidence_interval"] = confidence_interval

        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            analysis_result, extracted_claims, source_analysis, research_result
        )
        analysis_result["risk_factors"] = risk_factors

        return analysis_result

    def _calculate_confidence_interval(
        self,
        base_confidence: float,
        analysis_result: Dict[str, Any],
        source_analysis: List[SourceCredibility],
    ) -> Dict[str, float]:
        """
        Calculate confidence interval for the analysis.

        Args:
            base_confidence: Base confidence score
            analysis_result: Analysis results
            source_analysis: Source credibility analysis

        Returns:
            Confidence interval with lower and upper bounds
        """
        # Adjust confidence based on various factors
        adjustment_factors = []

        # Factor 1: Source credibility
        if source_analysis:
            avg_credibility = sum(s.credibility_score for s in source_analysis) / len(
                source_analysis
            )
            credibility_adjustment = (avg_credibility - 50) / 1000  # -0.05 to +0.05
            adjustment_factors.append(credibility_adjustment)

        # Factor 2: Number of citations
        citations_count = len(analysis_result.get("citations", []))
        citation_adjustment = min(citations_count * 0.02, 0.1)  # Up to +0.1
        adjustment_factors.append(citation_adjustment)

        # Factor 3: Verification steps complexity
        verification_steps = analysis_result.get("verification_steps", [])
        if verification_steps:
            complex_steps = sum(
                1 for step in verification_steps if step.get("complexity") == "complex"
            )
            complexity_adjustment = (
                -complex_steps * 0.03
            )  # Reduce confidence for complex verification
            adjustment_factors.append(complexity_adjustment)

        # Calculate total adjustment
        total_adjustment = sum(adjustment_factors)

        # Calculate bounds
        adjusted_confidence = max(0.1, min(0.9, base_confidence + total_adjustment))
        margin = 0.1 + (
            0.1 * (1 - adjusted_confidence)
        )  # Higher margin for lower confidence

        lower_bound = max(0.0, adjusted_confidence - margin)
        upper_bound = min(1.0, adjusted_confidence + margin)

        return {
            "lower_bound": round(lower_bound, 3),
            "upper_bound": round(upper_bound, 3),
        }

    def _identify_risk_factors(
        self,
        analysis_result: Dict[str, Any],
        extracted_claims: List[ExtractedClaim],
        source_analysis: List[SourceCredibility],
        research_result: Dict[str, Any],
    ) -> List[str]:
        """
        Identify risk factors that might indicate misinformation.

        Args:
            analysis_result: Analysis results
            extracted_claims: Extracted claims
            source_analysis: Source credibility analysis
            research_result: Research results

        Returns:
            List of risk factors
        """
        risk_factors = []

        # Check fake news rating
        rating = analysis_result.get("fake_news_rating", 3)
        if rating >= 4:
            risk_factors.append("High fake news rating")

        # Check source credibility
        if source_analysis:
            low_credibility_sources = [
                s for s in source_analysis if s.credibility_score < 60
            ]
            if low_credibility_sources:
                risk_factors.append(
                    f"Contains {len(low_credibility_sources)} low-credibility sources"
                )

            # Check for bias
            biased_sources = [
                s for s in source_analysis if s.bias_rating in ["left", "right"]
            ]
            if len(biased_sources) > 1:
                risk_factors.append("Multiple sources with strong political bias")

        # Check claims
        if extracted_claims:
            unverifiable_claims = [c for c in extracted_claims if not c.verifiable]
            if unverifiable_claims:
                risk_factors.append(
                    f"Contains {len(unverifiable_claims)} unverifiable claims"
                )

        # Check research quality
        if research_result.get("error"):
            risk_factors.append("Research verification failed")

        citations = analysis_result.get("citations", [])
        if len(citations) < 2:
            risk_factors.append("Limited citation sources")

        # Check verification complexity
        verification_steps = analysis_result.get("verification_steps", [])
        if verification_steps:
            complex_steps = [
                s for s in verification_steps if s.get("complexity") == "complex"
            ]
            if len(complex_steps) > 2:
                risk_factors.append("Requires complex verification process")

        return risk_factors[:5]  # Limit to top 5 risk factors

    def _calculate_batch_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics for batch processing.

        Args:
            results: List of batch processing results

        Returns:
            Batch summary statistics
        """
        successful_results = [r for r in results if r.get("status") == "success"]

        if not successful_results:
            return {
                "average_rating": 0,
                "average_confidence": 0,
                "most_common_risk_factors": [],
            }

        # Calculate average rating
        ratings = []
        confidences = []
        all_risk_factors = []

        for result in successful_results:
            result_data = result.get("result", {})
            if "fake_news_rating" in result_data:
                ratings.append(result_data["fake_news_rating"])
            if "confidence_score" in result_data:
                confidences.append(result_data["confidence_score"])
            if "risk_factors" in result_data:
                all_risk_factors.extend(result_data["risk_factors"])

        # Calculate averages
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Find most common risk factors
        risk_factor_counts = {}
        for factor in all_risk_factors:
            risk_factor_counts[factor] = risk_factor_counts.get(factor, 0) + 1

        most_common_factors = sorted(
            risk_factor_counts.items(), key=lambda x: x[1], reverse=True
        )[:3]

        return {
            "average_rating": round(avg_rating, 2),
            "average_confidence": round(avg_confidence, 3),
            "most_common_risk_factors": [
                factor for factor, count in most_common_factors
            ],
        }

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

        # Calculate confidence score based on available data (if not already present)
        if "confidence_score" not in analysis_result:
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

            explanation_length = len(fake_explanation) + len(true_explanation)
            if explanation_length > 0:
                length_score = min(
                    explanation_length / 1000.0, 1.0
                )  # Max at 1000 chars
                factors.append(length_score * 0.2)  # 20% weight

            # Factor 3: Source credibility
            source_analysis = analysis_result.get("source_analysis", [])
            if source_analysis:
                avg_credibility = sum(
                    s.get("credibility_score", 50) for s in source_analysis
                ) / len(source_analysis)
                credibility_score = avg_credibility / 100.0
                factors.append(credibility_score * 0.3)  # 30% weight

            # Factor 4: Verification steps
            verification_steps = analysis_result.get("verification_steps", [])
            if verification_steps:
                steps_score = min(len(verification_steps) / 3.0, 1.0)  # Max at 3 steps
                factors.append(steps_score * 0.2)  # 20% weight

            # Calculate final confidence
            if factors:
                return round(sum(factors), 3)
            else:
                return 0.5  # Default confidence

        except Exception as e:
            logger.warning(f"Failed to calculate confidence score: {str(e)}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the fact-checking service and all dependencies.

        Returns:
            Dictionary with health status of all components
        """
        try:
            # Check all service dependencies
            health_results = {}

            # Check Sonar client
            sonar_health = await self.sonar_client.health_check()
            health_results["sonar"] = sonar_health

            # Check LLM client (Groq or Anthropic)
            llm_health = await self.llm_client.health_check()
            provider_name = LLMFactory.get_provider_name(self.settings)
            health_results[provider_name] = llm_health

            # Check source credibility service
            source_health = await self.source_credibility_service.health_check()
            health_results["source_credibility"] = source_health

            # Check claim extraction service
            claim_health = await self.claim_extraction_service.health_check()
            health_results["claim_extraction"] = claim_health

            # Determine overall health
            all_healthy = all(
                result.get("status") == "healthy" for result in health_results.values()
            )

            health_results["overall"] = {
                "status": "healthy" if all_healthy else "degraded",
                "services_checked": len(health_results),
                "healthy_services": sum(
                    1
                    for result in health_results.values()
                    if result.get("status") == "healthy"
                ),
            }

            return health_results

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"overall": {"status": "unhealthy", "error": str(e)}}

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the fact-checking service.

        Returns:
            Dictionary with service information
        """
        provider_name = LLMFactory.get_provider_name(self.settings)

        return {
            "name": self.settings.app_name,
            "version": self.settings.app_version,
            "llm_provider": provider_name,
            "models": {
                provider_name: self.llm_client.get_available_models(),
                "perplexity": ["sonar-pro", "sonar"],
            },
            "current_models": {
                provider_name: LLMFactory.get_model_name(self.settings),
                "perplexity": self.settings.perplexity_model,
            },
            "limits": {
                "max_tokens": self.settings.max_tokens,
                "request_timeout": self.settings.request_timeout,
                "batch_size": 10,
            },
            "features": {
                "claim_extraction": True,
                "source_credibility": True,
                "batch_processing": True,
                "confidence_intervals": True,
                "risk_assessment": True,
            },
        }
