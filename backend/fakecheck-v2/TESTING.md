# FakeCheck API v2.0 - Testing Guide

This guide explains how to test the FakeCheck API using automated integration tests.

## 🚀 Quick Start

### Prerequisites

1. **Start the server** (in one terminal):
   ```bash
   uv run python main.py
   ```

2. **Run tests** (in another terminal):
   ```bash
   # Run all integration tests
   uv run test-integration
   
   # Or run specific test suites
   uv run test-fast        # Basic functionality tests
   uv run test-smoke       # Connectivity tests only
   uv run test-no-ai       # Tests without AI dependencies
   ```

## 🧪 Test Types

### 1. Integration Tests (All)
```bash
uv run test-integration
```
- **What it tests**: Complete API functionality with real AI services
- **Duration**: 5-10 minutes
- **Requirements**: Server running + API keys configured
- **Use case**: Full validation before deployment

### 2. Fast Tests
```bash
uv run test-fast
```
- **What it tests**: Core functionality with minimal AI calls
- **Duration**: 2-3 minutes
- **Requirements**: Server running + API keys configured
- **Use case**: Quick validation during development

### 3. Smoke Tests
```bash
uv run test-smoke
```
- **What it tests**: Basic connectivity and health endpoints
- **Duration**: 10-30 seconds (first call may take longer)
- **Requirements**: Server running only
- **Use case**: Quick server health check

### 4. No-AI Tests
```bash
uv run test-no-ai
```
- **What it tests**: All functionality except AI fact-checking
- **Duration**: 30-60 seconds
- **Requirements**: Server running only
- **Use case**: Testing when AI services are unavailable

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
uv sync --dev
```

### 2. Configure Environment
Create a `.env` file:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
ANTHROPIC_MODEL=claude-3-5-haiku-latest
PERPLEXITY_MODEL=sonar-pro
```

### 3. Start the Server
```bash
uv run python main.py
```

The server will be available at `http://localhost:8000`

## 📊 Test Coverage

### API Endpoints Tested
- ✅ `GET /v1/health` - Health check
- ✅ `GET /v1/info` - API information
- ✅ `POST /v1/check-fake` - Fact-checking

### Test Scenarios
- ✅ **Basic functionality**: Simple fact-checking requests
- ✅ **Custom prompts**: Advanced AI prompting
- ✅ **Complex content**: Multi-claim news analysis
- ✅ **Scientific facts**: Known true/false content
- ✅ **Input validation**: Error handling for invalid inputs
- ✅ **Malformed requests**: JSON parsing errors
- ✅ **Security headers**: CORS and security policies
- ✅ **Performance**: Response time validation
- ✅ **Concurrency**: Multiple simultaneous requests
- ✅ **Edge cases**: Special characters, short content, etc.

### Response Validation
- ✅ **Structure**: All required fields present
- ✅ **Types**: Correct data types for all fields
- ✅ **Ranges**: Valid rating ranges (1-5)
- ✅ **Content**: Non-empty explanations and steps
- ✅ **Metadata**: Processing time, timestamps, correlation IDs

## 🐛 Troubleshooting

### Common Issues

#### 1. Server Not Running
```
❌ Server is not running at http://localhost:8000
```
**Solution**: Start the server first:
```bash
uv run python main.py
```

#### 2. Missing API Keys
```
⚠️ ANTHROPIC_API_KEY not set
⚠️ PERPLEXITY_API_KEY not set
```
**Solution**: Set environment variables or create `.env` file

#### 3. Connection Errors
```
❌ Error: Connection refused
```
**Solution**: Check if server is running on correct port (8000)

#### 4. Test Failures
```
❌ Some tests failed!
```
**Solution**: 
- Check server logs for errors
- Verify API keys are valid
- Ensure internet connectivity
- Try running smoke tests first

### Debug Mode
For verbose output, run tests directly with pytest:
```bash
uv run pytest test_integration_live.py -v -s
```

## 📈 Performance Expectations

### Response Times
- **Health check**: < 100ms (first call may take 10-30s for AI initialization)
- **Info endpoint**: < 100ms
- **Simple fact-check**: < 30 seconds
- **Complex fact-check**: < 60 seconds

### Success Rates
- **Smoke tests**: 100% success expected
- **Integration tests**: 95%+ success expected
- **Concurrent tests**: 90%+ success expected

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Setup Python
        run: uv python install
      - name: Install dependencies
        run: uv sync --dev
      - name: Start server
        run: uv run python main.py &
      - name: Wait for server
        run: sleep 10
      - name: Run tests
        run: uv run test-integration
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
```

## 📝 Writing New Tests

### Test Structure
```python
def test_new_feature(self, http_client):
    """Test description."""
    # Arrange
    payload = {"news": "Test content"}
    
    # Act
    response = http_client.post("/v1/check-fake", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    self._validate_fact_check_response(data)
```

### Test Categories
Add pytest markers to new tests:
```python
@pytest.mark.slow
def test_long_running_feature(self):
    """Test that takes a while."""
    pass

@pytest.mark.integration
def test_external_api_integration(self):
    """Test with external APIs."""
    pass
```

## 📋 Test Checklist

Before deploying, ensure:
- [ ] All smoke tests pass
- [ ] Integration tests pass with >95% success rate
- [ ] Performance tests show acceptable response times
- [ ] Error handling works correctly
- [ ] Security headers are present
- [ ] Correlation IDs are unique
- [ ] API documentation is up to date

## 📞 Support

- **Issues**: Check logs and try smoke tests first
- **Performance**: Monitor response times and server resources
- **API Changes**: Update tests when endpoints change
- **Environment**: Verify all environment variables are set

## 🚀 Next Steps

1. **Load Testing**: Use tools like `locust` or `k6` for load testing
2. **Security Testing**: Run security scans on the API
3. **Monitoring**: Set up monitoring and alerting
4. **Documentation**: Keep tests and documentation in sync 