# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FakeCheck is a fake news detection system with three main components:
1. **FastAPI Backend** (`backend/fakecheck-v2/`) - AI-powered fact-checking API using Claude and Perplexica (with Perplexity Sonar fallback)
2. **Browser Extension** (`extension/`) - Chrome extension for real-time text analysis on web pages
3. **Twitter Bot** (`backend/fakecheck-v2/twitter-bot.py`) - Automated fact-checking via Twitter mentions

## Development Commands

### Backend Development

```bash
# Navigate to backend
cd backend/fakecheck-v2

# Install dependencies
uv sync

# Run the FastAPI server
python main.py
# or with auto-reload:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run the Twitter bot (separate process)
python twitter-bot.py
```

### Testing

The project uses a sophisticated test infrastructure with multiple test suites:

```bash
# Via pyproject.toml scripts (recommended):
uv run test-smoke         # 10-30s: Health checks only
uv run test-no-ai        # 30-60s: Skip external AI API tests
uv run test-fast         # 2-3 min: Core functionality with minimal AI calls
uv run test-integration  # 5-10 min: Complete suite with all external APIs

# Via shell scripts:
./run_tests.sh                           # Basic test suite
./run_integration_tests.sh              # Full integration tests
./run_integration_tests.sh --fast      # Fast subset
./run_integration_tests.sh --smoke     # Health checks only
./run_integration_tests.sh --no-ai     # No AI tests

# Via pytest directly:
pytest tests/ -v                        # All tests
pytest tests/ -m "not slow"            # Skip slow tests
pytest tests/ -m integration           # Integration tests only
pytest tests/ -m unit                  # Unit tests only
pytest tests/test_integration_live.py  # Live server tests
```

**Important**: Integration tests require the server to be running at `http://localhost:8000`.

### Code Quality

```bash
# Format code
black .

# Type checking
mypy src/

# Linting
flake8 src/
```

## Architecture

### Backend Structure

```
backend/fakecheck-v2/
├── main.py                    # FastAPI app entry point with lifespan, middleware
├── src/
│   ├── api/
│   │   └── routes/
│   │       └── fact_check.py  # V1 API endpoints
│   ├── services/
│   │   ├── fact_checker.py         # Main orchestration service
│   │   ├── anthropic_client.py     # Claude API client (structured output)
│   │   ├── perplexica_client.py    # Perplexica API client (open-source research)
│   │   ├── sonar_client.py         # Perplexity Sonar API client (fallback)
│   │   ├── claim_extraction.py     # Claim identification service
│   │   └── source_credibility.py   # Source analysis service
│   ├── models/
│   │   ├── requests.py        # Pydantic request models
│   │   └── responses.py       # Pydantic response models
│   └── core/
│       ├── config.py          # Settings with env validation
│       ├── exceptions.py      # Custom exception hierarchy
│       └── logging.py         # Structured logging with correlation IDs
├── tests/                     # Test suite
├── scripts/                   # Test runner scripts
└── pyproject.toml            # Project config, deps, tool settings
```

### API Endpoints (V1 prefix: `/v1`)

1. **POST /check-fake** - Primary fact-checking endpoint
   - Input: News text (required), custom prompt (optional)
   - Output: Rating (1-5), explanations, verification steps, citations
   - Multi-phase processing: Research → Claim extraction → Analysis → Enhancement

2. **POST /check-fake/batch** - Batch processing (up to 10 items)
   - Parallel or sequential processing
   - Aggregated statistics and summaries
   - Individual results with error handling

3. **POST /source-credibility** - Source credibility analysis
   - Input: URL, domain, or source name
   - Output: Credibility score (0-100), bias detection, factual accuracy
   - Similar source recommendations

4. **POST /extract-claims** - Extract verifiable claims
   - Input: Text content
   - Output: Claims with types (factual, opinion, statistical), confidence scores

5. **GET /health** - Service health check
   - Returns: Service status, dependency health (Perplexica, Perplexity Sonar, Anthropic/Groq)
   - Status codes: 200 (healthy), 503 (unhealthy)

6. **GET /info** - API information
   - Returns: Available endpoints, model versions, rate limits, features

### Fact-Checking Pipeline

The main `/check-fake` endpoint follows this flow:

```
1. Input Validation (FactCheckRequest)
2. Research Phase (Perplexica, with Perplexity Sonar fallback) - Web search for fact-checking
3. Claim Extraction (ClaimExtractionService) - Identify verifiable claims
4. AI Analysis (Anthropic Claude or Groq) - Analyze with structured output schema
5. Response Enhancement - Add metadata, processing time
6. Return FactCheckResponse
```

**Research Provider Priority:**
- Primary: Perplexica (open-source, self-hosted at localhost:3000)
- Fallback: Perplexity Sonar (if Perplexica fails or is unavailable)
- Configuration: Can be disabled/enabled via environment variables

### Middleware Chain

Requests pass through three middleware layers:

1. **CorrelationIdMiddleware** - Adds unique tracking ID to each request/response
2. **SecurityHeadersMiddleware** - Adds security headers (X-Content-Type-Options, etc.)
3. **CORSMiddleware** - Handles cross-origin requests (configurable origins)

### Error Handling

Custom exception hierarchy in `src/core/exceptions.py`:
- `FakeCheckError` (base)
  - `ValidationError`
  - `ExternalAPIError` (Anthropic/Perplexity/Perplexica failures)
    - `PerplexicaConnectionError`
    - `PerplexicaAPIError`
    - `PerplexityAPIError`
    - `AnthropicAPIError`
  - `ProcessingError`
  - `TimeoutError`
  - `RateLimitError`
  - `ConfigurationError`

All exceptions are caught by global handlers in `main.py` and returned as structured JSON with error codes, messages, and correlation IDs.

## Configuration

### Required Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
PERPLEXITY_API_KEY=pplx-...

# Twitter Bot (if using)
TWITTER_CONSUMER_KEY=...
TWITTER_CONSUMER_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
```

### Optional Environment Variables

```bash
# Model Selection
ANTHROPIC_MODEL=claude-3-5-haiku-latest  # Default
PERPLEXITY_MODEL=sonar-pro               # Default
LLM_PROVIDER=groq                        # groq or anthropic (default: groq)
GROQ_MODEL=llama-3.3-70b-versatile       # Default Groq model

# Perplexica Configuration (Open-Source Research Provider)
PERPLEXICA_ENABLED=true                          # Enable Perplexica (default: true)
PERPLEXICA_ENDPOINT=http://localhost:3000        # Perplexica API URL (default: localhost:3000)
PERPLEXICA_FOCUS_MODE=webSearch                  # webSearch, academicSearch, writingAssistant, wolframAlphaSearch, youtubeSearch, redditSearch (default: webSearch)
PERPLEXICA_OPTIMIZATION_MODE=balanced            # speed or balanced (default: balanced)
RESEARCH_FALLBACK_ENABLED=true                   # Enable fallback to Perplexity Sonar when Perplexica fails (default: true)

# API Configuration
MAX_TOKENS=4000                          # Default
REQUEST_TIMEOUT=30                       # Seconds
RATE_LIMIT_PER_MINUTE=100               # Requests per minute

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Logging
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR
DEBUG=false                              # Enable debug mode

# Custom Prompts (advanced)
BASE_PROMPT=<custom system prompt>       # Override default
```

Configuration is managed via `src/core/config.py` using Pydantic Settings with automatic validation.

## Key Implementation Details

### Anthropic Claude Integration

- Uses structured output with JSON schema (`article_schema`)
- Enforces consistent response format:
  - Fake news rating (1-5)
  - Explanations (both fake and true perspectives)
  - Verification steps (complexity levels, time estimates)
  - Confidence scores
- Async client with retry logic and error handling

### Perplexica Integration (Primary Research Provider)

- **Open-source AI-powered search engine** running on localhost:3000
- Combines multiple search engines with AI for comprehensive research
- **No API key required** (self-hosted)
- Supports multiple focus modes (web, academic, YouTube, Reddit, etc.)
- Automatically discovers and uses available AI providers (Groq, OpenAI, etc.)
- **Smart model selection**: Prefers general-purpose models (llama-3.3-70b-versatile, llama-3.1-8b-instant) over specialized ones
- **Automatic fallback**: Falls back to Perplexity Sonar if unavailable
- Provides citations from multiple sources
- Configurable optimization mode (speed vs balanced)

**Key Features:**
- Dynamic provider discovery via `/api/providers` endpoint
- Supports different providers for chat and embedding models
- Structured search results with sources and metadata
- Async HTTP client with proper timeout handling
- Health check monitoring integrated into `/v1/health` endpoint

**Fallback Behavior:**
1. Try Perplexica first (if `PERPLEXICA_ENABLED=true`)
2. If Perplexica fails (connection error, timeout, API error), fall back to Perplexity Sonar (if `RESEARCH_FALLBACK_ENABLED=true`)
3. If both fail, continue fact-checking with limited research context

### Perplexity Sonar Integration (Fallback Research Provider)

- Real-time web research for fact-checking
- Provides citations and reliable sources
- Uses `sonar-pro` model by default
- Research context fed into Claude/Groq for enhanced analysis
- Serves as automatic fallback when Perplexica is unavailable

### Browser Extension

The Chrome extension (`extension/`) allows users to:
1. Click on any paragraph (`<p>` tag) on a web page
2. Sends text to backend via `background.js`
3. Displays results via toast notification

**Key files:**
- `contentScript.js` - Injected into pages, handles click events
- `background.js` - Service worker, sends POST to `/check-fake`
- `popup.html/js` - Extension UI with "Check for Fake News" button
- `manifest.json` - Extension configuration and permissions

### Twitter Bot

The bot (`twitter-bot.py`):
- Monitors mentions via Twitter API v2
- Auto-replies with fact-check analysis
- Uses OAuth 1.0a authentication
- Tracks processed tweets in `last_tweet_id.txt`
- Update bot username on line 18 before use

## Testing Infrastructure

### Test Files

- `tests/test_fake_news_api.py` (370 lines) - Original unit/integration tests
- `tests/test_integration_live.py` (850 lines) - Comprehensive live server tests

### Test Categories

Tests are marked with pytest markers:
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.integration` - External API tests
- `@pytest.mark.unit` - Isolated component tests

Use `-m "not slow"` to skip slow tests, `-m integration` for integration only, etc.

### Test Coverage

Tests validate:
- Input validation and error handling
- Response format and data types
- Security headers and CORS
- Correlation ID tracking
- LLM response quality (rating ranges, explanation structure)
- Verification steps format (complexity, time estimates)
- Batch processing
- Source credibility scoring
- Claim extraction
- Health check endpoints
- Edge cases and malformed requests

### Running Tests Against Live Server

The integration tests expect a live server at `http://localhost:8000`. Start it before running:

```bash
# Terminal 1 - Start server
python main.py

# Terminal 2 - Run tests
./run_integration_tests.sh
```

## Code Patterns and Conventions

### Async-First Architecture

All I/O operations use `async`/`await`:
- FastAPI route handlers
- External API calls (Anthropic, Perplexity)
- Service methods in `FactCheckService`

### Dependency Injection

Services are injected via FastAPI's `Depends()`:
```python
@router.post("/check-fake")
async def check_fake(
    request: FactCheckRequest,
    fact_checker: FactCheckService = Depends(get_fact_checker)
):
    ...
```

### Structured Logging

All logs include correlation IDs for request tracking:
```python
logger.info("Processing request", extra={"correlation_id": correlation_id})
```

### Pydantic Models

All requests/responses use Pydantic V2 models for validation:
- Input validation happens automatically
- Type safety enforced
- Clear error messages for invalid data

### Service Layer Pattern

Business logic is isolated in services (`src/services/`):
- `FactCheckService` - Main orchestrator with fallback logic
- `PerplexicaClient` - Perplexica API wrapper (primary research)
- `SonarClient` - Perplexity API wrapper (fallback research)
- `AnthropicClient` / `GroqClient` - LLM API wrappers
- `ClaimExtractionService` - Claim identification
- `SourceCredibilityService` - Source analysis

Routes (`src/api/routes/`) are thin wrappers that delegate to services.

## Important Notes

### Cursor Rules

The `.cursor/rules/` directory contains reference documentation:
- `twitter-bot-docs.mdc` - Twitter API v2 bot creation guide (OAuth flow, deployment)
- `sonar-fact-check-example.mdc` - Perplexity Sonar fact-checking CLI reference

These are NOT active rules but helpful references for understanding the Twitter and Perplexity integrations.

### README Status

The main `README.md` describes the project vision but is marked as "Under Construction". The backend has its own comprehensive `README.md` and `TESTING.md`.

### Python Version

Project uses Python >=3.8.1 (see `pyproject.toml`). The `.python-version` file specifies the version for tools like `pyenv`.

### Security Considerations

- API keys should never be committed
- CORS origins should be restricted in production
- Rate limiting is configured (100 req/min default)
- Security headers are automatically added by middleware
- All external API calls have timeouts

### Browser Extension Endpoint

The extension currently POSTs to `http://0.0.0.0:8000/check-fake`. Update `background.js` if deploying to a different URL.
