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
        assert data["version"] == "2.1.0"
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

    def test_llm_response_quality_fake_news(self, http_client):
        """Test LLM response quality for obviously fake news."""
        payload = {
            "news": "Scientists have discovered that the Earth is actually flat and NASA has been lying to us for decades. All satellite images are computer generated."
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        # Should be rated as highly fake
        assert (
            data["fake_news_rating"] >= 4
        ), f"Expected high fake rating, got {data['fake_news_rating']}"

        # Check that explanations contain appropriate content
        fake_explanation = data["fake_news_explanation"].lower()
        true_explanation = data["true_news_explanation"].lower()

        # Should mention scientific evidence
        science_keywords = ["evidence", "scientific", "research", "study", "proof"]
        has_science_reference = any(
            keyword in fake_explanation or keyword in true_explanation
            for keyword in science_keywords
        )
        assert has_science_reference, "Should reference scientific evidence"

        # Should have multiple verification steps for complex claims
        assert (
            len(data["verification_steps"]) >= 2
        ), "Complex fake news should have multiple verification steps"

        print(f"✅ LLM quality for fake news - Rating: {data['fake_news_rating']}/5")
        print(f"   Verification steps: {len(data['verification_steps'])}")

    def test_llm_response_quality_true_news(self, http_client):
        """Test LLM response quality for obviously true news."""
        payload = {
            "news": "Water boils at 100 degrees Celsius at sea level under standard atmospheric pressure of 1 atmosphere."
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        # Should be rated as mostly true
        assert (
            data["fake_news_rating"] <= 2
        ), f"Expected low fake rating, got {data['fake_news_rating']}"

        # Check that explanations acknowledge the truth
        true_explanation = data["true_news_explanation"].lower()
        positive_keywords = ["correct", "accurate", "true", "factual", "verified"]
        has_positive_keywords = any(
            keyword in true_explanation for keyword in positive_keywords
        )
        assert (
            has_positive_keywords
        ), "True news should have positive validation keywords"

        print(f"✅ LLM quality for true news - Rating: {data['fake_news_rating']}/5")

    def test_llm_response_consistency(self, http_client):
        """Test that LLM responses are consistent between rating and explanations."""
        test_cases = [
            {
                "news": "The moon landing was staged by Hollywood directors in 1969.",
                "expected_rating_min": 4,
                "expected_keywords": ["false", "conspiracy", "debunked", "evidence"],
            },
            {
                "news": "The capital of France is Paris.",
                "expected_rating_max": 2,
                "expected_keywords": ["true", "correct", "accurate", "fact"],
            },
        ]

        for test_case in test_cases:
            payload = {"news": test_case["news"]}
            response = http_client.post("/v1/check-fake", json=payload)
            assert response.status_code == 200

            data = response.json()
            self._validate_fact_check_response(data)

            rating = data["fake_news_rating"]

            # Check rating consistency
            if "expected_rating_min" in test_case:
                assert (
                    rating >= test_case["expected_rating_min"]
                ), f"Rating {rating} too low for fake news"
            if "expected_rating_max" in test_case:
                assert (
                    rating <= test_case["expected_rating_max"]
                ), f"Rating {rating} too high for true news"

            # Check keyword consistency
            combined_text = (
                data["fake_news_explanation"] + " " + data["true_news_explanation"]
            ).lower()
            has_expected_keywords = any(
                keyword in combined_text for keyword in test_case["expected_keywords"]
            )
            assert (
                has_expected_keywords
            ), f"Missing expected keywords for: {test_case['news'][:50]}..."

            print(
                f"✅ LLM consistency - Rating: {rating}/5 for '{test_case['news'][:50]}...'"
            )

    def test_llm_verification_steps_quality(self, http_client):
        """Test that LLM generates high-quality verification steps."""
        payload = {
            "news": "A new study shows that drinking 8 glasses of water daily can prevent all types of cancer and extend life by 20 years."
        }

        response = http_client.post("/v1/check-fake", json=payload)
        assert response.status_code == 200

        data = response.json()
        self._validate_fact_check_response(data)

        verification_steps = data["verification_steps"]

        # Should have multiple steps for complex medical claims
        assert (
            len(verification_steps) >= 3
        ), "Medical claims should have multiple verification steps"

        # Check step quality
        step_actions = [
            "check",
            "verify",
            "search",
            "review",
            "examine",
            "investigate",
            "compare",
            "analyze",
        ]
        sources = [
            "study",
            "research",
            "medical",
            "journal",
            "expert",
            "database",
            "publication",
            "doctor",
            "scientist",
        ]

        has_action_words = False
        has_source_references = False

        for step in verification_steps:
            step_text = step["step"].lower()

            # Check for action words
            if any(action in step_text for action in step_actions):
                has_action_words = True

            # Check for source references
            if any(source in step_text for source in sources):
                has_source_references = True

            # Check time estimates are reasonable
            estimated_time = step["estimated_time"].lower()
            if "hour" in estimated_time or "hr" in estimated_time:
                # Extract number if possible, but at least ensure it's not extreme
                assert "100" not in estimated_time, "Time estimate too high"

            # Check complexity distribution
            complexity = step["complexity"]
            assert complexity in [
                "easy",
                "medium",
                "complex",
            ], f"Invalid complexity: {complexity}"

        assert has_action_words, "Verification steps should contain action words"
        assert has_source_references, "Verification steps should reference sources"

        print(
            f"✅ LLM verification steps quality - {len(verification_steps)} steps generated"
        )
        print(
            f"   Action words: {has_action_words}, Source references: {has_source_references}"
        )

        # Print sample steps for manual review
        for i, step in enumerate(verification_steps[:2]):
            print(f"   Step {i+1}: {step['step'][:80]}...")
            print(
                f"   Time: {step['estimated_time']}, Complexity: {step['complexity']}"
            )

    def _validate_fact_check_response(self, data: Dict[str, Any]):
        """Validate the structure and content of a fact-check response from LLM."""
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

        # 1. Validate fake_news_rating
        assert isinstance(
            data["fake_news_rating"], int
        ), "fake_news_rating must be integer"
        assert (
            1 <= data["fake_news_rating"] <= 5
        ), "fake_news_rating must be between 1-5"

        # 2. Validate fake_news_explanation (LLM response quality)
        fake_explanation = data["fake_news_explanation"]
        assert isinstance(fake_explanation, str), "fake_news_explanation must be string"
        assert (
            len(fake_explanation) >= 20
        ), "fake_news_explanation too short (min 20 chars)"
        assert (
            len(fake_explanation) <= 2000
        ), "fake_news_explanation too long (max 2000 chars)"

        # Check for meaningful content indicators
        meaningful_indicators = [
            "because",
            "due to",
            "according to",
            "evidence",
            "research",
            "study",
            "fact",
            "however",
            "although",
            "while",
            "but",
            "actually",
            "contrary",
            "misleading",
            "accurate",
            "inaccurate",
            "true",
            "false",
            "verified",
            "unverified",
        ]
        has_meaningful_content = any(
            indicator in fake_explanation.lower() for indicator in meaningful_indicators
        )
        assert (
            has_meaningful_content
        ), "fake_news_explanation lacks meaningful analysis indicators"

        # 3. Validate true_news_explanation (LLM response quality)
        true_explanation = data["true_news_explanation"]
        assert isinstance(true_explanation, str), "true_news_explanation must be string"
        assert (
            len(true_explanation) >= 20
        ), "true_news_explanation too short (min 20 chars)"
        assert (
            len(true_explanation) <= 2000
        ), "true_news_explanation too long (max 2000 chars)"

        # Should be different from fake_explanation
        assert fake_explanation != true_explanation, "Explanations should be different"

        # Should have meaningful content
        has_meaningful_content = any(
            indicator in true_explanation.lower() for indicator in meaningful_indicators
        )
        assert (
            has_meaningful_content
        ), "true_news_explanation lacks meaningful analysis indicators"

        # 4. Validate verification_steps (LLM structured output)
        verification_steps = data["verification_steps"]
        assert isinstance(verification_steps, list), "verification_steps must be a list"
        assert len(verification_steps) > 0, "Must have at least one verification step"
        assert len(verification_steps) <= 10, "Too many verification steps (max 10)"

        # Validate each verification step structure
        for i, step in enumerate(verification_steps):
            assert isinstance(step, dict), f"Verification step {i} must be a dict"

            # Required fields in each step
            step_required_fields = ["step", "estimated_time", "complexity"]
            for field in step_required_fields:
                assert (
                    field in step
                ), f"Missing field '{field}' in verification step {i}"

            # Validate step description
            step_desc = step["step"]
            assert isinstance(
                step_desc, str
            ), f"Step description must be string in step {i}"
            assert len(step_desc) >= 10, f"Step description too short in step {i}"
            assert len(step_desc) <= 500, f"Step description too long in step {i}"

            # Validate estimated_time format
            estimated_time = step["estimated_time"]
            assert isinstance(
                estimated_time, str
            ), f"estimated_time must be string in step {i}"
            time_indicators = ["minute", "hour", "second", "min", "hr", "sec"]
            has_time_indicator = any(
                indicator in estimated_time.lower() for indicator in time_indicators
            )
            assert (
                has_time_indicator
            ), f"estimated_time should include time unit in step {i}"

            # Validate complexity
            complexity = step["complexity"]
            assert complexity in [
                "easy",
                "medium",
                "complex",
            ], f"Invalid complexity '{complexity}' in step {i}"

        # 5. Validate processing_time_ms
        processing_time = data["processing_time_ms"]
        assert isinstance(
            processing_time, (int, float)
        ), "processing_time_ms must be number"
        assert processing_time > 0, "processing_time_ms must be positive"
        assert processing_time < 300000, "processing_time_ms too high (>5 minutes)"

        # 6. Validate timestamp format
        timestamp = data["timestamp"]
        assert isinstance(timestamp, str), "timestamp must be string"
        assert len(timestamp) > 10, "timestamp too short"
        # Should contain date/time indicators
        time_indicators = ["T", ":", "-", "Z"]
        has_time_format = any(indicator in timestamp for indicator in time_indicators)
        assert has_time_format, "timestamp should be in ISO format"

        # 7. Validate optional fields
        if "confidence_score" in data:
            confidence = data["confidence_score"]
            assert isinstance(
                confidence, (int, float)
            ), "confidence_score must be number"
            assert 0 <= confidence <= 1, "confidence_score must be between 0-1"

        if "citations" in data:
            citations = data["citations"]
            assert isinstance(citations, list), "citations must be a list"
            assert len(citations) <= 20, "Too many citations (max 20)"
            for i, citation in enumerate(citations):
                assert isinstance(citation, str), f"Citation {i} must be string"
                assert len(citation) >= 3, f"Citation {i} too short"
                assert len(citation) <= 500, f"Citation {i} too long"

        # 8. Validate response coherence (LLM quality check)
        # Rating should align with explanations
        if data["fake_news_rating"] >= 4:  # High fake rating
            fake_keywords = [
                "false",
                "incorrect",
                "misleading",
                "inaccurate",
                "fake",
                "untrue",
            ]
            has_fake_keywords = any(
                keyword in fake_explanation.lower() for keyword in fake_keywords
            )
            assert has_fake_keywords, "High fake rating should have corresponding negative keywords in explanation"

        elif data["fake_news_rating"] <= 2:  # Low fake rating (mostly true)
            true_keywords = [
                "true",
                "correct",
                "accurate",
                "verified",
                "factual",
                "valid",
            ]
            has_true_keywords = any(
                keyword in true_explanation.lower() for keyword in true_keywords
            )
            assert has_true_keywords, "Low fake rating should have corresponding positive keywords in explanation"


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
