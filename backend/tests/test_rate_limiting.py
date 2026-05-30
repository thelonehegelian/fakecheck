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
    """Test that health, info, and root endpoints are not rate limited even when quota is exceeded."""
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
                
                # 1. Exhaust the limit on a protected endpoint
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                
                # Confirm it is rate limited
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 429
                
                # 2. Health endpoint should still pass and NOT have rate limit headers
                response = await client.get("/v1/health")
                assert response.status_code in [200, 503]
                assert "X-RateLimit-Limit" not in response.headers
                
                # 3. Info endpoint should still pass and NOT have rate limit headers
                response = await client.get("/v1/info")
                assert response.status_code == 200
                assert "X-RateLimit-Limit" not in response.headers
                
                # 4. Root API endpoint should still pass
                response = await client.get("/")
                assert response.status_code == 200
                assert "X-RateLimit-Limit" not in response.headers

    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window


@pytest.mark.asyncio
async def test_rate_limiting_disabled_when_zero():
    """Test that rate limiting is completely disabled when rate_limit_requests is 0 or negative (B2)."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    
    try:
        # Set limit to 0 (disabled)
        settings.rate_limit_requests = 0
        settings.rate_limit_window = 10
        
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("src.services.fact_checker.FactCheckService.check_news") as mock_check:
                mock_check.return_value = {"fake_news_rating": 1, "fake_news_explanation": "Test", "true_news_explanation": "Test", "verification_steps": []}
                
                # Sending multiple requests should not block anything
                for _ in range(3):
                    response = await client.post(
                        "/v1/check-fake",
                        json={"news": "This is a valid test claim that meets the length requirement."}
                    )
                    assert response.status_code == 200
                    assert "X-RateLimit-Limit" not in response.headers

    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window


@pytest.mark.asyncio
async def test_rate_limiting_client_ip_isolation():
    """Test that different client IPs have isolated rate limit counts and X-Forwarded-For header is supported in hosted mode."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    orig_deployment = settings.deployment
    
    try:
        # Set limit to 1 request and deployment to hosted (so headers are trusted)
        settings.rate_limit_requests = 1
        settings.rate_limit_window = 10
        settings.deployment = "hosted"
        
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
                    headers={
                        "X-Forwarded-For": "203.0.113.195, 70.41.3.18",
                        "Origin": "chrome-extension://mgijgjcddggcjplglapehbchepmghbme",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "0"
                
                # IP A - Request 2 (Blocked)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={
                        "X-Forwarded-For": "203.0.113.195, 70.41.3.18",
                        "Origin": "chrome-extension://mgijgjcddggcjplglapehbchepmghbme",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
                assert response.status_code == 429
                
                # IP B - Request 1 (Allowed because IP B is different)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={
                        "X-Forwarded-For": "198.51.100.12",
                        "Origin": "chrome-extension://mgijgjcddggcjplglapehbchepmghbme",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
                assert response.status_code == 200
                assert response.headers["X-RateLimit-Remaining"] == "0"

    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window
        settings.deployment = orig_deployment


@pytest.mark.asyncio
async def test_rate_limiting_window_expiry():
    """Test that a client can make requests again after the rate limit window has expired (NB6)."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    
    try:
        # Set a 1 request limit with a 1 second window
        settings.rate_limit_requests = 1
        settings.rate_limit_window = 1
        
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("src.services.fact_checker.FactCheckService.check_news") as mock_check:
                mock_check.return_value = {"fake_news_rating": 1, "fake_news_explanation": "Test", "true_news_explanation": "Test", "verification_steps": []}
                
                # 1. First request is allowed
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                
                # 2. Second request is immediately blocked (within the 1s window)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 429
                
                # 3. Sleep past the window duration (1.2 seconds)
                await asyncio.sleep(1.2)
                
                # 4. Third request is allowed again because the window has reset
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."}
                )
                assert response.status_code == 200
                
    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window


@pytest.mark.asyncio
async def test_rate_limiting_spoof_protection_in_local():
    """Test that client-supplied proxy headers are ignored in local deployments (B1 spoofing protection)."""
    settings = get_settings()
    
    orig_requests = settings.rate_limit_requests
    orig_window = settings.rate_limit_window
    orig_deployment = settings.deployment
    
    try:
        # Set limit to 1 request and local deployment mode
        settings.rate_limit_requests = 1
        settings.rate_limit_window = 10
        settings.deployment = "local"
        
        app = create_app()
        
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("src.services.fact_checker.FactCheckService.check_news") as mock_check:
                mock_check.return_value = {"fake_news_rating": 1, "fake_news_explanation": "Test", "true_news_explanation": "Test", "verification_steps": []}
                
                # Request 1 with IP A header (Allowed)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={"X-Forwarded-For": "203.0.113.195"}
                )
                assert response.status_code == 200
                
                # Request 2 with IP B header (Blocked because local deployment ignores X-Forwarded-For
                # and falls back to client.host, treating both requests as same client)
                response = await client.post(
                    "/v1/check-fake",
                    json={"news": "This is a valid test claim that meets the length requirement."},
                    headers={"X-Forwarded-For": "198.51.100.12"}
                )
                assert response.status_code == 429
                
    finally:
        settings.rate_limit_requests = orig_requests
        settings.rate_limit_window = orig_window
        settings.deployment = orig_deployment
