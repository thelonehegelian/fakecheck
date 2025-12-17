# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a fake news detection system with two main components:
1. **FastAPI backend** (`main.py`) - Provides a `/check-fake` endpoint that analyzes news articles for authenticity using Claude AI and Exa search
2. **Twitter bot** (`twitter-bot.py`) - Monitors Twitter mentions and replies automatically

## Development Commands

### Python Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
python main.py

# Run the Twitter bot
python twitter-bot.py

# Run tests (requires API keys)
./run_tests.sh
# or manually:
pytest test_fake_news_api.py -v -s
```

### Dependencies
The project uses these key dependencies (imported in main.py):
- `fastapi` - Web framework
- `langchain-anthropic` - Claude AI integration
- `requests` - HTTP requests for Perplexity Sonar API
- `python-dotenv` - Environment variable management
- `requests-oauthlib` - Twitter API authentication
- `pydantic` - Data validation

## Architecture

### Main API Server (`main.py`)
- **FastAPI application** with CORS middleware
- **Single endpoint**: `POST /check-fake`
- **Process flow**:
  1. Accepts news text via POST request
  2. Researches the claim using Perplexity Sonar API for fact-checking
  3. Analyzes the news using Claude AI with structured output and research context
  4. Returns a JSON response with fake news rating (1-5), explanations, and verification steps

### Twitter Bot (`twitter-bot.py`)
- **Mention monitoring**: Searches for mentions of the bot using Twitter API v2
- **Auto-reply functionality**: Replies to mentions with a configurable message
- **State management**: Tracks last processed tweet ID to avoid duplicates
- **OAuth 1.0a authentication**: Uses Twitter API credentials

## Environment Variables

Required environment variables:
```bash
# Claude AI
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-haiku-latest  # Optional, defaults to claude-3-5-haiku-latest

# Perplexity Sonar API
PERPLEXITY_API_KEY=your_perplexity_api_key

# Twitter Bot
TWITTER_CONSUMER_KEY=your_twitter_consumer_key
TWITTER_CONSUMER_SECRET=your_twitter_consumer_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret

# Optional
BASE_PROMPT=custom_base_prompt  # Override default fake news detection prompt
```

## Key Implementation Details

### Structured Output Schema
The main API uses Claude's tool calling feature with a structured schema (`article_schema`) that enforces:
- Fake news rating (1-5 scale)
- Explanations for both fake and potentially true perspectives
- Verification steps with complexity levels and time estimates

### Research Integration
- Uses Perplexity Sonar API for comprehensive fact-checking research
- Leverages Sonar's real-time web search capabilities with citations
- Provides research context and reliable sources for fact verification

### Twitter Bot Configuration
- Bot username must be updated in `twitter-bot.py` (line 18)
- Uses persistent file storage (`last_tweet_id.txt`) to track processed tweets
- Configurable check interval (default: 60 seconds)

## Documentation

Additional documentation available in `docs/`:
- `twitter-bot-docs.md` - Comprehensive Twitter bot setup guide
- `sonar-api-docs.md` - Fact-checking CLI tool documentation
- `langchain-docs/tutorials.md` - LangChain integration tutorials

## Notes

- The README.md file is currently empty and should be populated with setup instructions
- No formal testing framework is configured
- No linting or code formatting tools are specified in the project configuration