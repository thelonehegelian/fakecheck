# Groq Integration Setup

Groq provides blazing-fast LLM inference (often 10x faster than other providers). This guide shows you how to use Groq with FakeCheck.

## Why Groq?

- ⚡ **Blazing Fast** - 2-5 seconds per fact-check vs 15-30 seconds with Claude
- 💰 **Cost Effective** - Lower cost per token
- 🦙 **Powerful Models** - Llama 3.3 70B is highly capable for fact-checking
- 🔄 **Drop-in Replacement** - Same LangChain interface

## Quick Start

### 1. Get a Groq API Key

1. Go to https://console.groq.com/
2. Sign up for a free account
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `gsk_...`)

### 2. Configure Environment

Add to your environment (Doppler or `.env`):

```bash
# Required
GROQ_API_KEY=gsk_your_key_here
PERPLEXITY_API_KEY=your_perplexity_key

# Optional - choose provider (defaults to groq)
LLM_PROVIDER=groq

# Optional - choose model (defaults to llama-3.3-70b-versatile)
GROQ_MODEL=llama-3.3-70b-versatile
```

**Using Doppler:**
```bash
doppler secrets set GROQ_API_KEY="gsk_your_key_here"
doppler secrets set LLM_PROVIDER="groq"
```

### 3. Start the Server

```bash
# With Doppler
doppler run -- python main.py

# Or with .env file
python main.py
```

You should see:
```
INFO - Using Groq as LLM provider with model: llama-3.3-70b-versatile
INFO - FakeCheck API v2.0 started successfully
```

### 4. Test It

```bash
curl -X POST http://localhost:8000/v1/check-fake \
  -H "Content-Type: application/json" \
  -d '{"news": "The moon landing was faked in 1969"}'
```

Response should be blazing fast (2-5 seconds)!

## Available Models

Groq supports these models (configured via `GROQ_MODEL`):

| Model | Description | Speed | Use Case |
|-------|-------------|-------|----------|
| `llama-3.3-70b-versatile` | Latest Llama 3.3 70B (default) | ⚡⚡⚡ | Best balance |
| `llama-3.1-70b-versatile` | Llama 3.1 70B | ⚡⚡⚡ | Production ready |
| `llama-3.1-8b-instant` | Llama 3.1 8B | ⚡⚡⚡⚡⚡ | Ultra fast |
| `mixtral-8x7b-32768` | Mixtral 8x7B | ⚡⚡⚡⚡ | Long context |
| `gemma2-9b-it` | Google Gemma 2 | ⚡⚡⚡⚡ | Efficient |

**Recommendation:** Use `llama-3.3-70b-versatile` (default) for best results.

## Switching Between Providers

You can easily switch between Groq and Anthropic:

### Use Groq (Fast & Cheap)
```bash
doppler secrets set LLM_PROVIDER="groq"
doppler secrets set GROQ_API_KEY="gsk_your_key"
```

### Use Anthropic Claude (High Quality)
```bash
doppler secrets set LLM_PROVIDER="anthropic"
doppler secrets set ANTHROPIC_API_KEY="sk-ant-your_key"
```

Restart the server to apply changes.

## Performance Comparison

Based on typical fact-checking requests:

| Provider | Model | Avg Time | Cost/1M tokens |
|----------|-------|----------|----------------|
| **Groq** | Llama 3.3 70B | ~3s | $0.59 |
| **Groq** | Llama 3.1 8B | ~1s | $0.05 |
| Anthropic | Claude Haiku | ~15s | $0.80 |
| Anthropic | Claude Sonnet | ~25s | $3.00 |

*Times are approximate and may vary based on request complexity and API load*

## Configuration Reference

### Environment Variables

```bash
# LLM Provider Selection
LLM_PROVIDER=groq                    # Options: groq, anthropic (default: groq)

# Groq Configuration
GROQ_API_KEY=gsk_...                 # Required if LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile  # Default model

# Anthropic Configuration (optional, for fallback)
ANTHROPIC_API_KEY=sk-ant-...         # Required if LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-3-5-haiku-latest  # Default model

# Research API (always required)
PERPLEXITY_API_KEY=pplx-...          # Required for all providers

# Server Configuration
MAX_TOKENS=4000                      # Max tokens per response
REQUEST_TIMEOUT=30                   # Timeout in seconds
```

## Troubleshooting

### Error: "GROQ_API_KEY is required"

Make sure you've set the API key:
```bash
doppler secrets get GROQ_API_KEY --plain
```

Should output your key. If not:
```bash
doppler secrets set GROQ_API_KEY="gsk_your_key_here"
```

### Error: "Invalid LLM provider"

Check your `LLM_PROVIDER` setting:
```bash
doppler secrets get LLM_PROVIDER --plain
```

Should be either `groq` or `anthropic`. Fix with:
```bash
doppler secrets set LLM_PROVIDER="groq"
```

### Slow Response Times

1. Check which provider is active:
   ```bash
   curl http://localhost:8000/v1/info | jq '.llm_provider'
   ```

2. Verify Groq is configured:
   ```bash
   doppler secrets get LLM_PROVIDER --plain
   ```

3. Try a faster model:
   ```bash
   doppler secrets set GROQ_MODEL="llama-3.1-8b-instant"
   ```

### API Rate Limits

Groq has generous rate limits on the free tier:
- 30 requests per minute
- 7,000 requests per day

If you hit limits, consider:
- Upgrading to a paid tier
- Implementing request queuing
- Using Anthropic as a fallback

## API Endpoints

All existing endpoints work with both providers:

- `POST /v1/check-fake` - Main fact-checking
- `POST /v1/check-fake/batch` - Batch processing
- `POST /v1/extract-claims` - Claim extraction
- `POST /v1/source-credibility` - Source analysis
- `GET /v1/health` - Health check (shows active provider)
- `GET /v1/info` - API info (shows provider & models)

## Health Check

Verify Groq is working:

```bash
curl http://localhost:8000/v1/health | jq '.'
```

Should show:
```json
{
  "status": "healthy",
  "services": {
    "groq": {
      "status": "healthy",
      "model_available": true
    },
    "sonar": {
      "status": "healthy"
    }
  }
}
```

## Best Practices

1. **Development**: Use Groq (fast iteration)
2. **Production**: Use Groq for speed, Anthropic for critical checks
3. **Testing**: Use `llama-3.1-8b-instant` for blazing fast tests
4. **Quality**: Use `llama-3.3-70b-versatile` for best results

## Support

- Groq Documentation: https://console.groq.com/docs
- Groq Discord: https://discord.gg/groq
- LangChain Groq: https://python.langchain.com/docs/integrations/chat/groq

## Next Steps

- Configure your Groq API key
- Test with a sample fact-check request
- Compare speed with Anthropic
- Update your browser extension to use the faster API
- Enjoy blazing-fast fact-checking! ⚡
