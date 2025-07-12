"""
Claim extraction service using AI to identify factual claims in text.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.core.config import Settings
from src.core.exceptions import ProcessingError, ValidationError
from src.services.anthropic_client import AnthropicClient
from src.models.responses import ExtractedClaim

logger = logging.getLogger(__name__)


class ClaimExtractionService:
    """Service for extracting claims from text content."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.anthropic_client = AnthropicClient(settings)

    async def extract_claims(
        self, text: str, extract_type: str = "factual", max_claims: int = 5
    ) -> List[ExtractedClaim]:
        """
        Extract claims from text content.

        Args:
            text: Text content to extract claims from
            extract_type: Type of claims to extract (factual, opinion, statistical, all)
            max_claims: Maximum number of claims to extract

        Returns:
            List of ExtractedClaim objects

        Raises:
            ValidationError: When input validation fails
            ProcessingError: When extraction fails
        """
        try:
            logger.info(
                f"Extracting {extract_type} claims from text ({len(text)} chars)"
            )

            # Validate input
            if not text.strip():
                raise ValidationError("Text content cannot be empty")

            if max_claims < 1 or max_claims > 20:
                raise ValidationError("max_claims must be between 1 and 20")

            # Create extraction prompt
            prompt = self._create_extraction_prompt(text, extract_type, max_claims)

            # Use Anthropic for extraction
            extraction_result = await self.anthropic_client.extract_claims(
                prompt=prompt,
                text=text,
                extract_type=extract_type,
                max_claims=max_claims,
            )

            # Parse results into ExtractedClaim objects
            claims = self._parse_extraction_results(extraction_result, text)

            logger.info(f"Successfully extracted {len(claims)} claims")
            return claims

        except Exception as e:
            logger.error(f"Claim extraction failed: {str(e)}")
            raise ProcessingError(f"Failed to extract claims: {str(e)}")

    def _create_extraction_prompt(
        self, text: str, extract_type: str, max_claims: int
    ) -> str:
        """
        Create a prompt for claim extraction.

        Args:
            text: Text content
            extract_type: Type of claims to extract
            max_claims: Maximum number of claims

        Returns:
            Extraction prompt string
        """
        type_descriptions = {
            "factual": "verifiable factual statements that can be confirmed or refuted",
            "opinion": "subjective opinions, beliefs, or judgments",
            "statistical": "claims involving numbers, percentages, or statistical data",
            "all": "all types of claims including factual, opinion, and statistical",
        }

        type_description = type_descriptions.get(extract_type, "factual claims")

        prompt = f"""
        Please extract {type_description} from the following text.
        
        Text to analyze:
        "{text}"
        
        Instructions:
        1. Extract up to {max_claims} {type_description}
        2. For each claim, provide:
           - The exact claim text
           - Claim type (factual, opinion, statistical, prediction, or other)
           - Confidence score (0-1) for how certain you are this is a claim
           - Whether the claim is verifiable (true/false)
           - Context (surrounding text that gives meaning to the claim)
        
        3. Focus on claims that are:
           - Specific and concrete
           - Potentially verifiable through research
           - Not overly broad or vague
           - Substantive (not trivial details)
        
        4. Avoid extracting:
           - Purely descriptive statements
           - Obvious facts (e.g., "The sky is blue")
           - Procedural instructions
           - Questions or hypotheticals
        
        Return the results in a structured format with clear separation between claims.
        """
        return prompt

    def _parse_extraction_results(
        self, extraction_result: Dict[str, Any], original_text: str
    ) -> List[ExtractedClaim]:
        """
        Parse AI extraction results into ExtractedClaim objects.

        Args:
            extraction_result: Results from AI extraction
            original_text: Original text for context

        Returns:
            List of ExtractedClaim objects
        """
        claims = []

        # Handle different result formats
        if "claims" in extraction_result:
            claims_data = extraction_result["claims"]
        elif "extracted_claims" in extraction_result:
            claims_data = extraction_result["extracted_claims"]
        elif isinstance(extraction_result, list):
            claims_data = extraction_result
        else:
            # Fallback: try to parse as a single claim
            claims_data = [extraction_result]

        for claim_data in claims_data:
            try:
                # Extract claim information
                claim_text = claim_data.get("claim", "")
                claim_type = claim_data.get("claim_type", "factual")
                confidence = float(claim_data.get("confidence", 0.5))
                verifiable = bool(claim_data.get("verifiable", True))
                context = claim_data.get("context", "")

                # Validate and clean up data
                if not claim_text.strip():
                    continue

                # Normalize claim type
                claim_type = self._normalize_claim_type(claim_type)

                # Ensure confidence is in valid range
                confidence = max(0.0, min(1.0, confidence))

                # Extract context if not provided
                if not context:
                    context = self._extract_context(claim_text, original_text)

                # Create ExtractedClaim object
                extracted_claim = ExtractedClaim(
                    claim=claim_text.strip(),
                    claim_type=claim_type,
                    confidence=confidence,
                    context=context,
                    verifiable=verifiable,
                )

                claims.append(extracted_claim)

            except Exception as e:
                logger.warning(f"Failed to parse claim: {str(e)}")
                continue

        return claims

    def _normalize_claim_type(self, claim_type: str) -> str:
        """
        Normalize claim type to valid values.

        Args:
            claim_type: Raw claim type from AI

        Returns:
            Normalized claim type
        """
        claim_type = claim_type.lower().strip()

        # Map variations to standard types
        type_mappings = {
            "fact": "factual",
            "facts": "factual",
            "factual": "factual",
            "opinion": "opinion",
            "opinions": "opinion",
            "subjective": "opinion",
            "statistical": "statistical",
            "statistics": "statistical",
            "numeric": "statistical",
            "numbers": "statistical",
            "prediction": "prediction",
            "predictions": "prediction",
            "forecast": "prediction",
            "claim": "factual",  # Default to factual
            "statement": "factual",
        }

        return type_mappings.get(claim_type, "other")

    def _extract_context(self, claim_text: str, original_text: str) -> str:
        """
        Extract context around a claim from the original text.

        Args:
            claim_text: The claim text
            original_text: Original text to search in

        Returns:
            Context surrounding the claim
        """
        try:
            # Find the claim in the original text
            claim_index = original_text.lower().find(claim_text.lower())

            if claim_index == -1:
                return ""

            # Extract context (50 characters before and after)
            context_start = max(0, claim_index - 50)
            context_end = min(len(original_text), claim_index + len(claim_text) + 50)

            context = original_text[context_start:context_end].strip()

            # Clean up context
            if context_start > 0:
                context = "..." + context
            if context_end < len(original_text):
                context = context + "..."

            return context

        except Exception as e:
            logger.warning(f"Failed to extract context: {str(e)}")
            return ""

    async def analyze_claim_verifiability(
        self, claim: ExtractedClaim
    ) -> Dict[str, Any]:
        """
        Analyze how a claim can be verified.

        Args:
            claim: ExtractedClaim object

        Returns:
            Dictionary with verification analysis
        """
        try:
            # Create verification analysis prompt
            prompt = f"""
            Analyze how this claim can be verified:
            
            Claim: "{claim.claim}"
            Type: {claim.claim_type}
            
            Please provide:
            1. Verification methods (how to check if this is true)
            2. Potential sources to consult
            3. Difficulty level (easy, medium, hard)
            4. Time estimate for verification
            5. Key terms or entities to research
            
            Consider:
            - What evidence would prove/disprove this claim?
            - What experts or authorities would know about this?
            - Are there databases or official records to check?
            - What search terms would be most effective?
            """

            # Use Anthropic for analysis
            analysis_result = await self.anthropic_client.analyze_claim_verifiability(
                prompt=prompt, claim=claim.claim
            )

            return {
                "verification_methods": analysis_result.get("verification_methods", []),
                "potential_sources": analysis_result.get("potential_sources", []),
                "difficulty_level": analysis_result.get("difficulty_level", "medium"),
                "time_estimate": analysis_result.get("time_estimate", "unknown"),
                "key_terms": analysis_result.get("key_terms", []),
                "searchability_score": analysis_result.get("searchability_score", 0.5),
            }

        except Exception as e:
            logger.warning(f"Claim verifiability analysis failed: {str(e)}")
            return {
                "verification_methods": ["Manual research required"],
                "potential_sources": ["General web search"],
                "difficulty_level": "medium",
                "time_estimate": "unknown",
                "key_terms": [],
                "searchability_score": 0.5,
            }

    async def get_extraction_summary(
        self, claims: List[ExtractedClaim]
    ) -> Dict[str, Any]:
        """
        Create a summary of extracted claims.

        Args:
            claims: List of ExtractedClaim objects

        Returns:
            Dictionary with extraction summary
        """
        if not claims:
            return {
                "total_claims_found": 0,
                "claim_types": {},
                "average_confidence": 0.0,
                "verifiable_claims": 0,
                "top_keywords": [],
            }

        # Count claim types
        claim_types = {}
        for claim in claims:
            claim_types[claim.claim_type] = claim_types.get(claim.claim_type, 0) + 1

        # Calculate average confidence
        total_confidence = sum(claim.confidence for claim in claims)
        average_confidence = total_confidence / len(claims)

        # Count verifiable claims
        verifiable_claims = sum(1 for claim in claims if claim.verifiable)

        # Extract top keywords (simple approach)
        all_text = " ".join(claim.claim for claim in claims)
        keywords = self._extract_keywords(all_text)

        return {
            "total_claims_found": len(claims),
            "claim_types": claim_types,
            "average_confidence": round(average_confidence, 3),
            "verifiable_claims": verifiable_claims,
            "top_keywords": keywords[:10],  # Top 10 keywords
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text (simple implementation).

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords
        """
        # Simple keyword extraction - in production, use NLP libraries
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "they",
            "them",
            "their",
        }

        # Extract words
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        # Count frequency
        word_counts = {}
        for word in keywords:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

        return [word for word, count in sorted_words]

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the claim extraction service is healthy.

        Returns:
            Dictionary with health status
        """
        try:
            # Test basic functionality
            test_text = (
                "Scientists have discovered that water boils at 100 degrees Celsius."
            )
            test_result = await self.extract_claims(test_text, max_claims=1)

            return {
                "status": "healthy",
                "test_extraction_successful": len(test_result) > 0,
                "anthropic_client_available": True,
            }
        except Exception as e:
            logger.warning(f"Claim extraction health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "anthropic_client_available": False,
            }
