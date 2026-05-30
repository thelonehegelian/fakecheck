import pytest
import asyncio
import time
from httpx import AsyncClient
from fastapi import FastAPI
from unittest.mock import patch

from src.core.config import get_settings, Settings
from src.core.exceptions import RateLimitError
from main import create_app


@pytest.mark.asyncio
async def test_rate_limiting_under_limit():
    """Test that requests within the rate limit are allowed and headers are returned."""
    settings = get_settings()
    
    # Save original settings
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    
    try:
        # Configure rate limit to 5 requests per 10 seconds
        settings.rate_limit_requests = 5
        settings.rate_limit_window = 10
        
        # Create a fresh app instance to initialize the middleware with updated settings
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Send first request to a v1 endpoint
            # Note: /v1/info is excluded, let's use a v1 endpoint that is rate-limited
            # Let's mock the fact check service to avoid calling actual LLMs
            with patch("src.services.fact_checker.FactCheckService.check_news") as mock_check:
                mock_check.return_value = {"fake_news_rating": 1, "fake_news_explanation": "Test", "true_news_explanation": "Test", "verification_steps": []}
                
                # First request
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                assert "X-RateLimit-Limit" in response.headers
                assert response.headers["X-RateLimit-Limit"] == "5"
                assert response.headers["X-RateLimit-Remaining"] == "4"
                assert "X-RateLimit-Reset" in response.headers
                
                # Second request
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "3"

    finally:
        # Restore settings
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window


@pytest.mark.asyncio
async def test_rate_limiting_exceeded():
    """Test that requests exceeding the limit are blocked with 429 and correct payload."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    
    try:
        # Set a very low limit for easy testing
        settings.rate_limit_requests = 2
        settings.rate_limit_window = 5
        
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("src.services.fact_checker.FactCheckService.check_news") as mock_check:
                mock_check.return_value = {"fake_news_rating": 1, "fake_news_explanation": "Test", "true_news_explanation": "Test", "verification_steps": []}
                
                # Request 1 (Allowed)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "1"
                
                # Request 2 (Allowed)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "0"
                
                # Request 3 (Blocked)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 429
                
                # Check response payload
                data = response.json()
                assert "error" in data
                assert data["error_code"] == "RATE_LIMIT_ERROR"
                assert "retry_after" in data["details"]
                assert data["details"]["retry_after"] > 0
                
                # Check headers
                assert "Retry-After" in response.headers
                assert response.headers["Retry-After"] == str(data["details"]["retry_after"])
                assert response.headers["X-RateLimit-Limit"] == "2"
                assert response.headers["X-RateLimit-Remaining"] == "0"
                assert int(response.headers["X-RateLimit-Reset"]) > 0

    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window


@pytest.mark.asyncio
async def test_rate_limiting_excludes_health_and_info():
    """Test that health, info, and root endpoints are not rate limited."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    
    try:
        # Set limit to 0 (all requests blocked if applied)
        settings.rate_limit_requests = 0
        settings.rate_limit_window = 10
        
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Health endpoint should pass and NOT have rate limit headers
            response = await client.get("/v1/health")
            assert response.status_code in [200, 503]
            assert "X-RateLimit-Limit" not in response.headers
            
            # 2. Info endpoint should pass and NOT have rate limit headers
            response = await client.get("/v1/info")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers
            
            # 3. Root API endpoint should pass
            response = await client.get("/")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers

    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window


@pytest.mark.asyncio
async def test_rate_limiting_client_ip_isolation():
    """Test that different client IPs have isolated rate limit counts and X-Forwarded-For header is supported."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    
    try:
        # Set limit to 1 request
        settings.rate_limit_requests = 1
        settings.rate_limit_window = 10
        
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("src.services.fact_checker.FactCheckService.check_news") as mock_check:
                mock_check.return_value = {"fake_news_rating": 1, "fake_news_explanation": "Test", "true_news_explanation": "Test", "verification_steps": []}
                
                # IP A - Request 1 (Allowed)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "0"
                
                # IP A - Request 2 (Blocked)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
                )
                assert response.status_code == 429
                
                # IP B - Request 1 (Allowed because IP B is different)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={"X-Forwarded-For": "198.51.100.12"}
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "0"

    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window
