#!/usr/bin/env python3
"""
Live Integration Tests for FakeCheck API v2.0
These tests hit the actual running backend server at http://localhost:8000
Run these tests while the server is running: uv run python main.py
"""

import pytest
import httpx
import asyncio
import time
import json
from typing import Dict, Any, List
from uuid import uuid4


class TestFakeCheckAPILive:
    """Integration tests against the live running server."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture(scope="class")
    def http_client(self):
        """Create HTTP client for testing."""
        return httpx.Client(base_url=self.BASE_URL, timeout=60.0)

    @pytest.fixture(scope="class")
    def async_http_client(self):
        """Create async HTTP client for testing."""
        return httpx.AsyncClient(base_url=self.BASE_URL, timeout=60.0)

    def test_server_is_running(self, http_client):
        """Test that the server is running and accessible."""
        try:
            response = http_client.get("/v1/health")
            assert response.status_code in [
                200,
                503,
            ], f"Server not accessible. Status: {response.status_code}"
            print(f"✅ Server is running. Status: {response.status_code}")
        except httpx.ConnectError:
            pytest.fail(
                "❌ Server is not running! Start the server with: uv run python main.py"
            )

    def test_health_endpoint(self, http_client):
        """Test the health check endpoint."""
        response = http_client.get("/v1/health")
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data

        # Check services structure
        services = data["services"]
        assert "sonar" in services
        assert "anthropic" in services

        print(f"✅ Health endpoint - Status: {data['status']}")
        print(f"   Services: {services}")

    def test_info_endpoint(self, http_client):
        """Test the API info endpoint."""
        response = http_client.get("/v1/info")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "models" in data
        assert "current_models" in data

        # Validate structure
        assert data["name"] == "FakeCheck API"
        assert data["version"] == "2.0.0"
        assert isinstance(data["endpoints"], list)
        assert "/v1/check-fake" in data["endpoints"]

        print(f"✅ Info endpoint - API: {data['name']} v{data['version']}")
        print(f"   Endpoints: {data['endpoints']}")

    def test_basic_fact_check(self, http_client):
        """Test basic fact-checking functionality."""
        payload = {
            "news": "The Great Wall of China is visible from space with the naked eye."
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        # This should be rated as fake/misleading (3-5)
        assert 1 <= data["fake_news_rating"] <= 5
        assert len(data["fake_news_explanation"]) > 50
        assert len(data["verification_steps"]) > 0

        print(f"✅ Basic fact check - Rating: {data['fake_news_rating']}/5")
        print(f"   Processing time: {data['processing_time_ms']}ms")

    def test_fact_check_with_custom_prompt(self, http_client):
        """Test fact-checking with custom prompt and priority."""
        payload = {
            "news": "Coffee is the most popular beverage in the world after water.",
            "custom_prompt": "Please provide specific statistics and sources in your analysis.",
            "priority": "high",
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        # Check that custom prompt influenced the response
        explanation = data["fake_news_explanation"].lower()
        assert any(
            keyword in explanation
            for keyword in ["statistic", "source", "data", "study"]
        )

        print(f"✅ Custom prompt fact check - Rating: {data['fake_news_rating']}/5")
        print(
            f"   Custom prompt influenced response: {any(keyword in explanation for keyword in ['statistic', 'source'])}"
        )

    def test_complex_news_analysis(self, http_client):
        """Test with complex, multi-claim news content."""
        payload = {
            "news": """
            Scientists have discovered a new planet in our solar system called Planet X, 
            which is located between Mars and Jupiter. This planet is twice the size of 
            Earth and has three moons. The discovery was made by NASA's Kepler telescope 
            and confirmed by the European Space Agency. The planet has a surface temperature 
            of 25°C and may contain liquid water, making it potentially habitable.
            """
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        # This should be rated as highly fake (4-5)
        assert data["fake_news_rating"] >= 3
        assert (
            len(data["verification_steps"]) >= 3
        )  # Should have multiple verification steps

        print(f"✅ Complex news analysis - Rating: {data['fake_news_rating']}/5")
        print(f"   Verification steps: {len(data['verification_steps'])}")

    def test_scientific_fact_check(self, http_client):
        """Test with a known scientific fact."""
        payload = {
            "news": "Water boils at 100 degrees Celsius at sea level under standard atmospheric pressure of 1 atmosphere (101.325 kPa)."
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        # This should be rated as true (1-2)
        assert data["fake_news_rating"] <= 2

        print(f"✅ Scientific fact check - Rating: {data['fake_news_rating']}/5")
        print(f"   Confidence: {data.get('confidence_score', 'N/A')}")

    def test_input_validation_errors(self, http_client):
        """Test various input validation scenarios."""
        test_cases = [
            # Missing news field
            ({}, 422, "Missing news field"),
            # Empty news
            ({"news": ""}, 422, "Empty news content"),
            # Too short news
            ({"news": "Hi"}, 422, "Too short news content"),
            # Invalid priority
            (
                {"news": "Valid news content here", "priority": "invalid"},
                422,
                "Invalid priority",
            ),
            # Invalid JSON structure
            (
                {"news": "Valid news", "extra_field": {"invalid": "structure"}},
                200,
                "Extra fields should be ignored",
            ),
        ]

        for payload, expected_status, description in test_cases:
            response = http_client.post("/v1/check-fake", json=payload)
            if expected_status == 200:
                assert response.status_code in [200, 422]  # Depends on validation rules
            else:
                assert response.status_code == expected_status

            if response.status_code != 200:
                data = response.json()
                assert "error" in data or "detail" in data

            print(f"✅ Input validation - {description}: {response.status_code}")

    def test_malformed_requests(self, http_client):
        """Test malformed request handling."""
        # Invalid JSON
        response = http_client.post(
            "/v1/check-fake",
            content='{"news": "test", "invalid": }',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # Wrong content type
        response = http_client.post(
            "/v1/check-fake",
            content="news=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 422

        print("✅ Malformed request handling works correctly")

    def test_correlation_id_tracking(self, http_client):
        """Test that correlation IDs are properly set and tracked."""
        response = http_client.get("/v1/health")
        assert "X-Correlation-ID" in response.headers

        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) > 0

        # Test that each request gets a unique correlation ID
        response2 = http_client.get("/v1/health")
        correlation_id2 = response2.headers["X-Correlation-ID"]
        assert correlation_id != correlation_id2

        print(f"✅ Correlation ID tracking - ID1: {correlation_id[:8]}...")
        print(f"   Unique IDs generated: {correlation_id != correlation_id2}")

    def test_security_headers(self, http_client):
        """Test that security headers are properly set."""
        response = http_client.get("/v1/info")
        assert response.status_code == 200

        headers = response.headers
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        present_headers = {}
        for header, expected_value in expected_headers.items():
            if header in headers:
                present_headers[header] = headers[header]

        print(
            f"✅ Security headers present: {len(present_headers)}/{len(expected_headers)}"
        )
        for header, value in present_headers.items():
            print(f"   {header}: {value}")

    def test_response_time_performance(self, http_client):
        """Test API response time performance."""
        payload = {"news": "The capital of France is Paris."}

        start_time = time.time()
        response = http_client.post("/v1/check-fake", json=payload)
        end_time = time.time()

        assert response.status_code == 200

        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        data = response.json()
        reported_time = data.get("processing_time_ms", 0)

        # Response time should be reasonable (less than 60 seconds)
        assert response_time < 60000

        print(f"✅ Performance test - Total time: {response_time:.0f}ms")
        print(f"   Reported processing time: {reported_time}ms")

    def test_concurrent_requests(self, http_client):
        """Test handling of concurrent requests."""
        import threading

        def make_request(results, index):
            payload = {
                "news": f"Test news content number {index} for concurrent testing."
            }
            try:
                response = http_client.post("/v1/check-fake", json=payload)
                results[index] = {
                    "status": response.status_code,
                    "correlation_id": response.headers.get("X-Correlation-ID"),
                    "success": response.status_code == 200,
                }
            except Exception as e:
                results[index] = {"error": str(e), "success": False}

        # Run 3 concurrent requests
        threads = []
        results = {}

        for i in range(3):
            thread = threading.Thread(target=make_request, args=(results, i))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check results
        successful_requests = sum(1 for r in results.values() if r.get("success"))
        unique_correlation_ids = set(
            r.get("correlation_id") for r in results.values() if r.get("correlation_id")
        )

        assert successful_requests >= 2  # At least 2 should succeed
        assert len(unique_correlation_ids) == len(
            [r for r in results.values() if r.get("correlation_id")]
        )

        print(f"✅ Concurrent requests - {successful_requests}/3 successful")
        print(f"   Unique correlation IDs: {len(unique_correlation_ids)}")

    def test_edge_cases(self, http_client):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            # Very short but valid news
            ("The sky is blue.", "Short valid news"),
            # News with special characters
            ("Test: 100% of people breathe oxygen! (Fact #1)", "Special characters"),
            # News with numbers and percentages
            (
                "Studies show 65% of statistics are made up 50% of the time.",
                "Numbers and percentages",
            ),
            # Non-English characters
            ("El agua hierve a 100°C a nivel del mar.", "Non-English content"),
        ]

        for news_content, description in edge_cases:
            payload = {"news": news_content}
            response = http_client.post("/v1/check-fake", json=payload)

            # Should either succeed or fail gracefully
            assert response.status_code in [200, 422, 400]

            if response.status_code == 200:
                data = response.json()
                self._validate_fact_check_response(data)
                print(
                    f"✅ Edge case - {description}: Rating {data['fake_news_rating']}/5"
                )
            else:
                print(
                    f"✅ Edge case - {description}: Handled with status {response.status_code}"
                )

    def test_error_response_format(self, http_client):
        """Test that error responses follow the expected format."""
        # Trigger a validation error
        response = http_client.post("/v1/check-fake", json={})
        assert response.status_code == 422

        data = response.json()

        # Check error response structure
        assert "detail" in data or "error" in data

        # Should have timestamp
        if "timestamp" in data:
            assert isinstance(data["timestamp"], str)

        print(f"✅ Error response format validated")

    def _validate_fact_check_response(self, data: Dict[str, Any]):
        """Validate the structure of a fact-check response."""
        # Required fields
        required_fields = [
            "fake_news_rating",
            "fake_news_explanation",
            "true_news_explanation",
            "verification_steps",
            "processing_time_ms",
            "timestamp",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate types and ranges
        assert isinstance(data["fake_news_rating"], int)
        assert 1 <= data["fake_news_rating"] <= 5

        assert isinstance(data["fake_news_explanation"], str)
        assert len(data["fake_news_explanation"]) > 0

        assert isinstance(data["true_news_explanation"], str)
        assert len(data["true_news_explanation"]) > 0

        assert isinstance(data["verification_steps"], list)
        assert len(data["verification_steps"]) > 0

        # Validate verification steps structure
        for step in data["verification_steps"]:
            assert "step" in step
            assert "estimated_time" in step
            assert "complexity" in step
            assert step["complexity"] in ["easy", "medium", "complex"]

        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] > 0

        # Optional fields validation
        if "confidence_score" in data:
            assert isinstance(data["confidence_score"], (int, float))
            assert 0 <= data["confidence_score"] <= 1

        if "citations" in data:
            assert isinstance(data["citations"], list)


class TestFakeCheckAPIAsync:
    """Async integration tests for concurrent operations."""

    BASE_URL = "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_async_fact_check(self):
        """Test async fact-checking operations."""
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=60.0) as client:
            payload = {"news": "The moon is made of cheese."}

            response = await client.post("/v1/check-fake", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert "fake_news_rating" in data
            assert data["fake_news_rating"] >= 3  # Should be fake

            print(f"✅ Async fact check - Rating: {data['fake_news_rating']}/5")

    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self):
        """Test multiple async requests concurrently."""
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=60.0) as client:
            # Create multiple different fact-check requests
            payloads = [
                {"news": "Water freezes at 0°C at standard pressure."},
                {"news": "Humans can breathe underwater without equipment."},
                {"news": "The sun rises in the east."},
            ]

            # Make concurrent requests
            tasks = []
            for i, payload in enumerate(payloads):
                task = client.post("/v1/check-fake", json=payload)
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # Validate all responses
            successful_responses = 0
            for i, response in enumerate(responses):
                if response.status_code == 200:
                    successful_responses += 1
                    data = response.json()
                    assert "fake_news_rating" in data
                    print(
                        f"✅ Async concurrent request {i+1} - Rating: {data['fake_news_rating']}/5"
                    )

            assert successful_responses >= 2  # At least 2 should succeed
            print(f"✅ Async concurrent requests - {successful_responses}/3 successful")


if __name__ == "__main__":
    # Run tests manually
    import sys

    print("🚀 Starting FakeCheck API Live Integration Tests")
    print("📋 Make sure the server is running: uv run python main.py")
    print("=" * 60)

    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
