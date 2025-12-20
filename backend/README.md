# FakeCheck API v2.0

A modern, scalable fact-checking service using AI research and analysis. Built with FastAPI, async operations, and comprehensive error handling.

## 🚀 Features

- **AI-Powered Analysis**: Uses Anthropic Claude or Groq for intelligent fact-checking
- **Web Research**: Leverages Perplexica (open-source) with Perplexity Sonar API fallback for real-time research
- **Automatic Fallback**: Seamless fallback from Perplexica to Perplexity Sonar if needed
- **Async Operations**: Built on FastAPI with async/await for high performance
- **Structured Output**: Returns detailed analysis with ratings, explanations, and verification steps
- **Comprehensive Error Handling**: Proper HTTP status codes and error responses
- **Security**: CORS policies, security headers, and input validation
- **Monitoring**: Correlation IDs for request tracking and structured logging
- **Health Checks**: Built-in health monitoring for all services (Perplexica, Sonar, LLM)
- **API Versioning**: Proper versioning with backward compatibility

## 🏗️ Architecture

The API is built with a clean, modular architecture:

```
src/
├── api/
│   └── routes/          # API route handlers
├── services/            # Business logic services
│   ├── fact_checker.py         # Main orchestration service with fallback logic
│   ├── perplexica_client.py    # Perplexica API client (primary)
│   ├── sonar_client.py         # Perplexity Sonar API client (fallback)
│   ├── anthropic_client.py     # Anthropic API client
│   ├── groq_client.py          # Groq API client
│   └── llm_factory.py          # LLM provider factory
├── models/              # Pydantic models
│   ├── requests.py      # Request models
│   └── responses.py     # Response models
├── core/                # Core utilities
│   ├── config.py        # Configuration management
│   ├── exceptions.py    # Custom exceptions
│   └── logging.py       # Logging configuration
└── main.py              # Application entry point
```

## 🔧 Installation

### Prerequisites

- Python 3.8.1+
- [uv](https://docs.astral.sh/uv/) - Modern Python package manager
- [Perplexica](https://github.com/ItzCrazyKns/Perplexica) running on localhost:3000 (recommended for research)
- API keys for:
  - Anthropic Claude API or Groq API (for LLM analysis)
  - Perplexity Sonar API (optional, used as fallback if Perplexica unavailable)

### Setup

1. **Install uv (if not already installed)**
```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv

# Or via pip
pip install uv
```

2. **Clone the repository**
```bash
git clone <repository-url>
cd fakecheck-v2
```

3. **Install dependencies**
```bash
# Install project dependencies and create virtual environment
uv sync

# For development dependencies
uv sync --dev
```

3. **Set environment variables**
```bash
# Required (choose one LLM provider)
export GROQ_API_KEY="your_groq_api_key"              # For Groq (default, fast)
# OR
export ANTHROPIC_API_KEY="your_anthropic_api_key"   # For Anthropic Claude

# Optional (for fallback research)
export PERPLEXITY_API_KEY="your_perplexity_api_key"
```

Or create a `.env` file:
```env
# LLM Provider (choose one)
LLM_PROVIDER=groq                           # groq or anthropic (default: groq)
GROQ_API_KEY=your_groq_api_key             # If using Groq
GROQ_MODEL=llama-3.3-70b-versatile         # Default Groq model
# ANTHROPIC_API_KEY=your_anthropic_api_key  # If using Anthropic
# ANTHROPIC_MODEL=claude-3-5-haiku-latest    # Default Claude model

# Research Providers
PERPLEXICA_ENABLED=true                     # Enable Perplexica (default: true)
PERPLEXICA_ENDPOINT=http://localhost:3000   # Perplexica URL
PERPLEXICA_FOCUS_MODE=webSearch             # webSearch, academicSearch, etc.
PERPLEXICA_OPTIMIZATION_MODE=balanced       # speed or balanced
RESEARCH_FALLBACK_ENABLED=true              # Fallback to Perplexity if Perplexica fails
PERPLEXITY_API_KEY=your_perplexity_api_key  # Only needed if fallback enabled
PERPLEXITY_MODEL=sonar-pro                  # Default Perplexity model

# Server Configuration
LOG_LEVEL=INFO
DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
REQUEST_TIMEOUT=30
```

4. **Run the application**
```bash
# Run with uv (recommended)
uv run python main.py

# Or run uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Development with uv

**Common uv commands:**
```bash
# Create/update the virtual environment and install dependencies
uv sync

# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name

# Run scripts in the virtual environment
uv run python script.py
uv run pytest
uv run black .
uv run mypy src/

# Run tests
uv run pytest test_fake_news_api.py -v
# Or use the provided script
./run_tests.sh
```

## 📊 API Usage

### Base URL
```
http://localhost:8000
```

### Authentication
No authentication required for basic usage.

### Endpoints

#### 1. Fact Check News Content
**POST** `/v1/check-fake`

Analyze news content for factual accuracy.

**Request Body:**
```json
{
  "news": "The Great Wall of China is visible from space.",
  "custom_prompt": "Please be extra thorough in your analysis.",
  "priority": "normal"
}
```

**Response:**
```json
{
  "fake_news_rating": 4,
  "fake_news_explanation": "This is a common misconception. The Great Wall is not visible from space with the naked eye according to NASA astronauts.",
  "true_news_explanation": "The Great Wall is an impressive structure, but it's too narrow and similar in color to surrounding terrain to be visible from space without aid.",
  "verification_steps": [
    {
      "step": "Check NASA's official statements about visibility from space",
      "estimated_time": "5 minutes",
      "complexity": "easy"
    },
    {
      "step": "Research astronaut testimonies about what's visible from space",
      "estimated_time": "10 minutes", 
      "complexity": "medium"
    }
  ],
  "citations": [
    "NASA - Visibility of human-made structures from space",
    "Astronaut testimonies on space visibility"
  ],
  "processing_time_ms": 3500,
  "confidence_score": 0.85,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 2. Health Check
**GET** `/v1/health`

Check the health status of the API and its dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "2.0.0",
  "services": {
    "sonar": "healthy",
    "anthropic": "healthy"
  }
}
```

#### 3. API Information
**GET** `/v1/info`

Get information about the API capabilities and configuration.

**Response:**
```json
{
  "name": "FakeCheck API",
  "version": "2.0.0",
  "description": "A fact-checking service using AI research and analysis",
  "endpoints": ["/v1/check-fake", "/v1/health", "/v1/info"],
  "models": {
    "anthropic": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
    "perplexity": ["sonar-pro", "sonar"]
  },
  "current_models": {
    "anthropic": "claude-3-5-haiku-latest",
    "perplexity": "sonar-pro"
  }
}
```

## 🔍 Response Format

### Success Response
All successful responses include:
- **Processing metadata**: `processing_time_ms`, `timestamp`
- **Confidence scoring**: `confidence_score` (0-1 scale)
- **Source citations**: `citations` array
- **Correlation ID**: Via `X-Correlation-ID` header

### Error Response
All error responses follow a consistent format:
```json
{
  "error": "Description of the error",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z",
  "details": {
    "field": "news",
    "additional_info": "..."
  }
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad request (validation error)
- `408`: Request timeout
- `422`: Unprocessable entity (validation error)
- `429`: Rate limit exceeded
- `500`: Internal server error
- `502`: External API error
- `503`: Service unavailable

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `PERPLEXITY_API_KEY` | Perplexity API key | Required |
| `ANTHROPIC_MODEL` | Anthropic model to use | `claude-3-5-haiku-latest` |
| `PERPLEXITY_MODEL` | Perplexity model to use | `sonar-pro` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Enable debug mode | `false` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000,http://localhost:3001` |
| `MAX_TOKENS` | Max tokens for AI responses | `4000` |
| `REQUEST_TIMEOUT` | Request timeout in seconds | `30` |

## 🧪 Testing

### Quick Start with uv Scripts

The easiest way to test the API is using the built-in uv scripts:

```bash
# 1. Start the server (in one terminal)
uv run python main.py

# 2. Run tests (in another terminal)
uv run test-integration   # Full integration tests
uv run test-fast         # Quick functionality tests  
uv run test-smoke        # Basic connectivity tests
uv run test-no-ai        # Tests without AI dependencies
```

### Manual Testing with pytest

```bash
# Install test dependencies
uv sync --dev

# Run all integration tests
uv run pytest tests/test_integration_live.py

# Run with verbose output
uv run pytest tests/test_integration_live.py -v -s

# Run specific test categories
uv run pytest -m "not slow"  # Skip slow tests
uv run pytest -m "integration"  # Only integration tests
uv run pytest -m "unit"  # Only unit tests
```

### Test Types

| Command | Description | Duration | Requirements |
|---------|-------------|----------|--------------|
| `uv run test-smoke` | Basic connectivity | 10-30s* | Server running |
| `uv run test-no-ai` | All except AI endpoints | 30-60s | Server running |
| `uv run test-fast` | Core functionality | 2-3 min | Server + API keys |
| `uv run test-integration` | Complete test suite | 5-10 min | Server + API keys |

*First call may take longer due to AI service initialization

For detailed testing instructions, see [TESTING.md](TESTING.md).

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints with real external services
- **Health Tests**: Test service health and monitoring endpoints

### Writing Tests

The test suite includes:
- Async test support with `pytest-asyncio`
- Mock external API calls for unit tests
- Real API integration tests (require API keys)
- Comprehensive error scenario testing

## 📈 Monitoring & Logging

### Correlation IDs
Every request gets a unique correlation ID for tracking across services:
```
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Structured Logging
All logs include:
- Timestamp
- Log level
- Component name
- Correlation ID
- Structured message

Example log:
```
2024-01-15 10:30:00 - src.services.fact_checker - INFO - [550e8400-e29b-41d4-a716-446655440000] - Starting fact-check for news: The Great Wall of China...
```

### Health Monitoring
- `/v1/health` endpoint provides detailed health status
- Monitors external API connectivity
- Includes service uptime and performance metrics

## 🔒 Security

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Input Validation
- Request size limits (10KB for news content)
- Content-type validation
- Parameter validation with Pydantic models

### CORS Policy
Configurable CORS origins for frontend integration.

## 📖 API Documentation

### Interactive Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Rate Limiting
Built-in rate limiting configuration (configurable):
- 100 requests per minute per IP
- Proper HTTP 429 responses with `Retry-After` headers

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use environment variables for API keys
- Configure proper CORS origins
- Set up monitoring and alerting
- Use reverse proxy (nginx) for load balancing
- Configure SSL/TLS certificates

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt -e ".[dev]"

# Run code formatting
black src/

# Run linting
flake8 src/

# Run type checking
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Check the `/docs` endpoint for API documentation
- **Health Status**: Monitor API health via `/v1/health`

## 🔄 Changelog

### v2.0.0 (Current)
- Complete architecture refactor
- Async operations throughout
- Improved error handling
- Structured logging with correlation IDs
- Health monitoring and API versioning
- Comprehensive test suite
- Security improvements

### v1.0.0
- Basic fact-checking functionality
- Synchronous operations
