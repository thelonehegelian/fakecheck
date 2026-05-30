"""
Quick test script for Perplexica integration.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, "/Users/leviathan/_CS/_projects/fake-check/backend")

from src.core.config import Settings
from src.services.perplexica_client import PerplexicaClient


async def test_perplexica():
    """Test Perplexica client health check and basic research."""
    print("=== Perplexica Integration Test ===\n")

    # Create settings with Perplexica enabled
    settings = Settings(
        perplexica_enabled=True,
        perplexica_endpoint="http://localhost:3000",
        perplexica_focus_mode="webSearch",
        perplexica_optimization_mode="balanced",
        perplexity_api_key="dummy",  # Not used if Perplexica works
        research_fallback_enabled=False,  # Disable fallback for this test
    )

    print(f"Perplexica endpoint: {settings.perplexica_endpoint}")
    print(f"Focus mode: {settings.perplexica_focus_mode}")
    print(f"Optimization mode: {settings.perplexica_optimization_mode}\n")

    # Create client
    client = PerplexicaClient(settings)

    # Test 1: Health check
    print("Test 1: Health Check")
    print("-" * 50)
    try:
        health = await client.health_check()
        print(f"Health Status: {health.get('status')}")
        print(f"Models Available: {health.get('models_available')}")
        print(f"Providers Count: {health.get('providers_count')}")
        print(f"Endpoint: {health.get('endpoint')}")

        if health.get("status") == "healthy":
            print("✓ Health check PASSED\n")
        else:
            print(f"✗ Health check FAILED: {health.get('error')}\n")
            return
    except Exception as e:
        print(f"✗ Health check FAILED with exception: {str(e)}\n")
        return

    # Test 2: Simple research query
    print("Test 2: Research Query")
    print("-" * 50)
    try:
        result = await client.research_claim(
            text="What is the capital of France?"
        )

        print(f"Content Length: {len(result.get('content', ''))} characters")
        print(f"Citations Count: {len(result.get('citations', []))}")
        print(f"Model Used: {result.get('model_used')}")
        print(f"\nFirst 200 chars of content:")
        print(result.get('content', '')[:200])

        if result.get('citations'):
            print(f"\nFirst citation: {result['citations'][0]}")

        print("\n✓ Research query PASSED\n")
    except Exception as e:
        print(f"✗ Research query FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()

    # Close client
    await client.client.aclose()

    print("=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_perplexica())
