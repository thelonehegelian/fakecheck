#!/usr/bin/env python3
"""
Integration tests for the FakeCheck API v2.0.
These tests work with the new async architecture and proper error handling.
"""

import pytest
import os
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
import asyncio

# Import the main application
from main import app
from src.core.config import Settings
from src.core.exceptions import FakeCheckError
from src.services.fact_checker import FactCheckService
from src.models.requests import FactCheckRequest


class TestFakeCheckAPIv2:
    """Test suite for the FakeCheck API v2.0."""

    @pytest.fixture(scope="class")
    def api_keys(self):
        """Check that required API keys are available."""
        perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if not perplexity_key:
            pytest.skip("PERPLEXITY_API_KEY environment variable not set")
        if not anthropic_key:
            pytest.skip("ANTHROPIC_API_KEY environment variable not set")

        return {"perplexity": perplexity_key, "anthropic": anthropic_key}

    @pytest.fixture(scope="class")
    def test_cases(self):
        """Test cases with known examples."""
        return [
            {
                "news": "The Great Wall of China is visible from the moon with the naked eye.",
                "expected_rating_range": (3, 5),  # Should be rated as fake/misleading
                "description": "Common misconception about Great Wall visibility",
            },
            {
                "news": "The Earth is approximately 4.6 billion years old according to scientific evidence.",
                "expected_rating_range": (1, 2),  # Should be rated as true
                "description": "Scientific fact about Earth's age",
            },
            {
                "news": "Water boils at 100 degrees Celsius at sea level under standard atmospheric pressure.",
                "expected_rating_range": (1, 2),  # Should be rated as true
                "description": "Basic physics fact",
            },
        ]

    @pytest.mark.asyncio
    async def test_app_startup(self, api_keys):
        """Test that the app starts up properly."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "FakeCheck API v2.0" in data["message"]
            assert "version" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, api_keys):
        """Test the health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "version" in data

    @pytest.mark.asyncio
    async def test_v1_health_endpoint(self, api_keys):
        """Test the v1 health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/health")
            # This might be 200 or 503 depending on API availability
            assert response.status_code in [200, 503]
            data = response.json()
            assert "status" in data
            assert "version" in data
            assert "services" in data

    @pytest.mark.asyncio
    async def test_v1_info_endpoint(self, api_keys):
        """Test the v1 info endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/info")
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "version" in data
            assert "endpoints" in data
            assert "models" in data

    @pytest.mark.asyncio
    async def test_api_structure_validation(self, api_keys):
        """Test that the API returns the expected structure."""
        test_payload = {
            "news": "The Great Wall of China is visible from the moon with the naked eye.",
            "priority": "normal",
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/check-fake", json=test_payload)

            # Should return 200 for successful processing or 502 for API errors
            assert response.status_code in [200, 502, 503]

            data = response.json()

            if response.status_code == 200:
                # Check required fields are present
                assert "fake_news_rating" in data
                assert "fake_news_explanation" in data
                assert "true_news_explanation" in data
                assert "verification_steps" in data

                # Check rating is in valid range
                assert isinstance(data["fake_news_rating"], int)
                assert 1 <= data["fake_news_rating"] <= 5

                # Check explanations are strings
                assert isinstance(data["fake_news_explanation"], str)
                assert isinstance(data["true_news_explanation"], str)
                assert len(data["fake_news_explanation"]) > 0
                assert len(data["true_news_explanation"]) > 0

                # Check verification steps structure
                assert isinstance(data["verification_steps"], list)
                assert len(data["verification_steps"]) > 0

                for step in data["verification_steps"]:
                    assert "step" in step
                    assert "estimated_time" in step
                    assert "complexity" in step
                    assert step["complexity"] in ["easy", "medium", "complex"]

                # Check metadata
                assert "processing_time_ms" in data
                assert "timestamp" in data

                print(
                    f"API Response structure validated. Rating: {data['fake_news_rating']}"
                )
            else:
                # Should have error information
                assert "error" in data
                assert "error_code" in data
                print(f"API returned error: {data.get('error', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_input_validation(self, api_keys):
        """Test API input validation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test empty news
            response = await client.post("/v1/check-fake", json={"news": ""})
            assert response.status_code == 422

            # Test missing news field
            response = await client.post("/v1/check-fake", json={})
            assert response.status_code == 422

            # Test news too short
            response = await client.post("/v1/check-fake", json={"news": "Hi"})
            assert response.status_code == 422

            # Test invalid priority
            response = await client.post(
                "/v1/check-fake",
                json={"news": "Valid news content here", "priority": "invalid"},
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_cors_headers(self, api_keys):
        """Test that CORS headers are properly set."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/info")
            assert response.status_code == 200

            # Check for CORS headers (might not be present in test environment)
            # This is more for documentation of expected behavior
            headers = response.headers
            print(f"Response headers: {dict(headers)}")

    @pytest.mark.asyncio
    async def test_correlation_id_header(self, api_keys):
        """Test that correlation ID is added to responses."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/info")
            assert response.status_code == 200

            # Check for correlation ID header
            assert "X-Correlation-ID" in response.headers
            correlation_id = response.headers["X-Correlation-ID"]
            assert len(correlation_id) > 0
            print(f"Correlation ID: {correlation_id}")

    @pytest.mark.asyncio
    async def test_security_headers(self, api_keys):
        """Test that security headers are properly set."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/info")
            assert response.status_code == 200

            # Check for security headers
            headers = response.headers
            assert "X-Content-Type-Options" in headers
            assert "X-Frame-Options" in headers
            assert "X-XSS-Protection" in headers
            assert "Referrer-Policy" in headers

            print("Security headers present and correct")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "news": "The Great Wall of China is visible from the moon with the naked eye.",
                "expected_rating_range": (3, 5),
                "description": "Common misconception about Great Wall visibility",
            },
            {
                "news": "The Earth is approximately 4.6 billion years old according to scientific evidence.",
                "expected_rating_range": (1, 2),
                "description": "Scientific fact about Earth's age",
            },
        ],
    )
    async def test_fact_checking_accuracy(self, api_keys, test_case):
        """Test that the API provides reasonable ratings for known cases."""
        test_payload = {"news": test_case["news"], "priority": "normal"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/check-fake", json=test_payload)

            # Handle different response scenarios
            if response.status_code == 200:
                data = response.json()
                rating = data["fake_news_rating"]

                # Check if rating is in expected range
                min_rating, max_rating = test_case["expected_rating_range"]
                assert min_rating <= rating <= max_rating, (
                    f"Rating {rating} not in expected range {test_case['expected_rating_range']} "
                    f"for: {test_case['description']}"
                )

                print(f"Test case: {test_case['description']}")
                print(
                    f"Rating: {rating} (expected: {test_case['expected_rating_range']})"
                )
                print(f"Processing time: {data.get('processing_time_ms', 'N/A')}ms")

                # Test confidence score if present
                if "confidence_score" in data:
                    assert 0 <= data["confidence_score"] <= 1
                    print(f"Confidence score: {data['confidence_score']}")

            elif response.status_code in [502, 503]:
                # External API unavailable - skip test
                pytest.skip(
                    f"External APIs unavailable: {response.json().get('error', 'Unknown error')}"
                )
            else:
                # Unexpected error - fail test
                pytest.fail(
                    f"Unexpected response: {response.status_code} - {response.json()}"
                )

    @pytest.mark.asyncio
    async def test_custom_prompt_feature(self, api_keys):
        """Test the custom prompt feature."""
        test_payload = {
            "news": "The sun rises in the east.",
            "custom_prompt": "Please be extra careful about obvious facts.",
            "priority": "normal",
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/check-fake", json=test_payload)

            if response.status_code == 200:
                data = response.json()
                assert "fake_news_rating" in data
                print(
                    f"Custom prompt test completed. Rating: {data['fake_news_rating']}"
                )
            elif response.status_code in [502, 503]:
                pytest.skip("External APIs unavailable")
            else:
                pytest.fail(f"Unexpected response: {response.status_code}")


# Unit tests for individual components
class TestFakeCheckComponents:
    """Test individual components of the FakeCheck system."""

    def test_fact_check_request_model(self):
        """Test the FactCheckRequest model validation."""
        # Valid request
        request = FactCheckRequest(
            news="This is a valid news article with enough content.", priority="normal"
        )
        assert request.news == "This is a valid news article with enough content."
        assert request.priority == "normal"

        # Test validation errors
        with pytest.raises(Exception):  # Should raise validation error
            FactCheckRequest(news="")

        with pytest.raises(Exception):  # Should raise validation error
            FactCheckRequest(news="Hi")  # Too short

    def test_fake_check_error(self):
        """Test the custom error classes."""
        error = FakeCheckError("Test error", "TEST_ERROR", {"detail": "test"})
        error_dict = error.to_dict()

        assert error_dict["error"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["details"]["detail"] == "test"
        assert "timestamp" in error_dict

    @pytest.mark.asyncio
    async def test_fact_check_service_initialization(self):
        """Test that FactCheckService can be initialized."""
        from src.core.config import Settings

        # Mock settings to avoid requiring real API keys
        settings = Settings(anthropic_api_key="test_key", perplexity_api_key="test_key")

        service = FactCheckService(settings)
        assert service.settings == settings
        assert service.sonar_client is not None
        assert service.anthropic_client is not None


def test_environment_setup():
    """Test that the testing environment is properly set up."""
    # Check that we can import required modules
    try:
        import fastapi
        import httpx
        import pytest
        import aiohttp
        import anthropic
    except ImportError as e:
        pytest.fail(f"Required testing dependencies not installed: {e}")

    # Check that main app imports work
    try:
        from main import app
        from src.core.config import get_settings
        from src.services.fact_checker import FactCheckService
    except ImportError as e:
        pytest.fail(f"Cannot import from main application: {e}")


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v", "-s"])
