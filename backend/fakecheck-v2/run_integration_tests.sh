#!/bin/bash

# FakeCheck API v2.0 - Integration Test Runner
# This script runs comprehensive integration tests against the live running server

set -e

echo "🚀 FakeCheck API v2.0 - Integration Test Runner"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if server is running
echo "🔍 Checking if server is running..."
if curl -s --max-time 5 http://localhost:8000/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is running at http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Server is not running!${NC}"
    echo "Please start the server first:"
    echo "  uv run python main.py"
    echo ""
    echo "Or in another terminal:"
    echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    exit 1
fi

# Check if required dependencies are installed
echo ""
echo "🔍 Checking test dependencies..."
if ! python -c "import httpx, pytest" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Installing test dependencies...${NC}"
    uv add --dev pytest httpx pytest-asyncio
fi

# Check API keys
echo ""
echo "🔍 Checking API keys..."
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    echo -e "${YELLOW}⚠️  ANTHROPIC_API_KEY not set${NC}"
fi
if [[ -z "$PERPLEXITY_API_KEY" ]]; then
    echo -e "${YELLOW}⚠️  PERPLEXITY_API_KEY not set${NC}"
fi

# Get server info
echo ""
echo "📊 Server Information:"
SERVER_INFO=$(curl -s http://localhost:8000/v1/info)
echo "$SERVER_INFO" | python -m json.tool

echo ""
echo "🧪 Running Integration Tests..."
echo "================================="

# Run the tests
if [[ "$1" == "--fast" ]]; then
    echo "Running fast tests only..."
    uv run pytest test_integration_live.py::TestFakeCheckAPILive::test_server_is_running \
                  test_integration_live.py::TestFakeCheckAPILive::test_health_endpoint \
                  test_integration_live.py::TestFakeCheckAPILive::test_info_endpoint \
                  test_integration_live.py::TestFakeCheckAPILive::test_basic_fact_check \
                  test_integration_live.py::TestFakeCheckAPILive::test_input_validation_errors \
                  -v --tb=short
elif [[ "$1" == "--smoke" ]]; then
    echo "Running smoke tests only..."
    uv run pytest test_integration_live.py::TestFakeCheckAPILive::test_server_is_running \
                  test_integration_live.py::TestFakeCheckAPILive::test_health_endpoint \
                  test_integration_live.py::TestFakeCheckAPILive::test_info_endpoint \
                  -v --tb=short
elif [[ "$1" == "--no-ai" ]]; then
    echo "Running tests without AI endpoints..."
    uv run pytest test_integration_live.py::TestFakeCheckAPILive::test_server_is_running \
                  test_integration_live.py::TestFakeCheckAPILive::test_health_endpoint \
                  test_integration_live.py::TestFakeCheckAPILive::test_info_endpoint \
                  test_integration_live.py::TestFakeCheckAPILive::test_input_validation_errors \
                  test_integration_live.py::TestFakeCheckAPILive::test_malformed_requests \
                  test_integration_live.py::TestFakeCheckAPILive::test_correlation_id_tracking \
                  test_integration_live.py::TestFakeCheckAPILive::test_security_headers \
                  test_integration_live.py::TestFakeCheckAPILive::test_error_response_format \
                  -v --tb=short
else
    echo "Running all integration tests..."
    uv run pytest test_integration_live.py -v --tb=short
fi

TEST_RESULT=$?

echo ""
echo "📈 Test Results Summary:"
echo "========================"

if [[ $TEST_RESULT -eq 0 ]]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "🎉 Your FakeCheck API is working correctly!"
    echo ""
    echo "Next steps:"
    echo "• Run load tests: ./run_integration_tests.sh --load"
    echo "• Check logs for any warnings"
    echo "• Monitor API performance"
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "• Check server logs for errors"
    echo "• Verify API keys are correct"
    echo "• Ensure external APIs are accessible"
    echo "• Check network connectivity"
fi

echo ""
echo "📋 Test Options:"
echo "• --fast    : Run basic tests only"
echo "• --smoke   : Run smoke tests only"
echo "• --no-ai   : Skip AI-dependent tests"
echo "• (default) : Run all tests"

exit $TEST_RESULT 