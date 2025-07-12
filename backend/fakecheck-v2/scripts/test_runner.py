#!/usr/bin/env python3
"""
Test runner module for FakeCheck API v2.0
Provides different test execution functions for uv scripts
"""

import sys
import subprocess
import requests
from typing import List, Optional
import time


def _check_server_running(url: str = "http://localhost:8000") -> bool:
    """Check if the server is running."""
    try:
        print("🔍 Checking server health (this may take up to 30 seconds)...")
        response = requests.get(f"{url}/v1/health", timeout=30)
        return response.status_code in [200, 503]
    except requests.RequestException as e:
        print(f"❌ Server check failed: {e}")
        return False


def _print_banner(title: str):
    """Print a formatted banner."""
    print(f"\n🚀 {title}")
    print("=" * (len(title) + 3))


def _print_server_info():
    """Print server information."""
    try:
        response = requests.get("http://localhost:8000/v1/info", timeout=30)
        if response.status_code == 200:
            info = response.json()
            print(
                f"📊 Server: {info.get('name', 'Unknown')} v{info.get('version', 'Unknown')}"
            )
            print(f"🔗 Endpoints: {', '.join(info.get('endpoints', []))}")
        else:
            print("📊 Server info not available")
    except requests.RequestException as e:
        print(f"📊 Could not retrieve server info: {e}")


def _run_pytest(test_patterns: List[str], description: str) -> int:
    """Run pytest with given patterns."""
    if not _check_server_running():
        print("❌ Server is not running at http://localhost:8000")
        print("Please start the server first:")
        print("  uv run python main.py")
        print("\nOr in another terminal:")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        return 1

    _print_banner(f"FakeCheck API - {description}")
    print("🔍 Server is running ✅")
    _print_server_info()

    print(f"\n🧪 Running {description.lower()}...")
    print("=" * 50)

    # Build pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *test_patterns,
        "-v",
        "--tb=short",
        "--disable-warnings",
    ]

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


def run_integration_tests() -> int:
    """Run all integration tests."""
    return _run_pytest(["test_integration_live.py"], "Integration Tests (All)")


def run_fast_tests() -> int:
    """Run fast integration tests."""
    patterns = [
        "test_integration_live.py::TestFakeCheckAPILive::test_server_is_running",
        "test_integration_live.py::TestFakeCheckAPILive::test_health_endpoint",
        "test_integration_live.py::TestFakeCheckAPILive::test_info_endpoint",
        "test_integration_live.py::TestFakeCheckAPILive::test_basic_fact_check",
        "test_integration_live.py::TestFakeCheckAPILive::test_input_validation_errors",
        "test_integration_live.py::TestFakeCheckAPILive::test_correlation_id_tracking",
    ]
    return _run_pytest(patterns, "Fast Integration Tests")


def run_smoke_tests() -> int:
    """Run smoke tests (basic connectivity)."""
    patterns = [
        "test_integration_live.py::TestFakeCheckAPILive::test_server_is_running",
        "test_integration_live.py::TestFakeCheckAPILive::test_health_endpoint",
        "test_integration_live.py::TestFakeCheckAPILive::test_info_endpoint",
    ]
    return _run_pytest(patterns, "Smoke Tests")


def run_no_ai_tests() -> int:
    """Run tests that don't require AI APIs."""
    patterns = [
        "test_integration_live.py::TestFakeCheckAPILive::test_server_is_running",
        "test_integration_live.py::TestFakeCheckAPILive::test_health_endpoint",
        "test_integration_live.py::TestFakeCheckAPILive::test_info_endpoint",
        "test_integration_live.py::TestFakeCheckAPILive::test_input_validation_errors",
        "test_integration_live.py::TestFakeCheckAPILive::test_malformed_requests",
        "test_integration_live.py::TestFakeCheckAPILive::test_correlation_id_tracking",
        "test_integration_live.py::TestFakeCheckAPILive::test_security_headers",
        "test_integration_live.py::TestFakeCheckAPILive::test_error_response_format",
    ]
    return _run_pytest(patterns, "Tests (No AI Dependencies)")


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="FakeCheck API Test Runner")
    parser.add_argument(
        "test_type",
        choices=["integration", "fast", "smoke", "no-ai"],
        help="Type of tests to run",
    )

    args = parser.parse_args()

    if args.test_type == "integration":
        return run_integration_tests()
    elif args.test_type == "fast":
        return run_fast_tests()
    elif args.test_type == "smoke":
        return run_smoke_tests()
    elif args.test_type == "no-ai":
        return run_no_ai_tests()
    else:
        print(f"Unknown test type: {args.test_type}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
