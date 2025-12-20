# Perplexica Integration Guide

## Overview

FakeCheck now uses **Perplexica** as the primary research provider, with automatic fallback to Perplexity Sonar. Perplexica is an open-source AI-powered search engine that runs on your local machine.

## ✨ Benefits

- **No API costs** - Perplexica is self-hosted and free
- **Privacy-focused** - All searches run on your own hardware
- **Multiple search engines** - Combines results from various sources
- **Automatic fallback** - Seamlessly switches to Perplexity Sonar if Perplexica is unavailable
- **Flexible configuration** - Easy to enable/disable via environment variables

## 🚀 Quick Start

### 1. Install Perplexica

Follow the [official Perplexica installation guide](https://github.com/ItzCrazyKns/Perplexica):

```bash
# Using Docker (recommended)
docker run -d -p 3000:3000 \
  -v perplexica-data:/home/perplexica/data \
  -v perplexica-uploads:/home/perplexica/uploads \
  --name perplexica \
  itzcrazykns1337/perplexica:latest
```

### 2. Configure FakeCheck

Add these environment variables to your `.env` file:

```bash
# Enable Perplexica
PERPLEXICA_ENABLED=true
PERPLEXICA_ENDPOINT=http://localhost:3000

# Configure search behavior
PERPLEXICA_FOCUS_MODE=webSearch
PERPLEXICA_OPTIMIZATION_MODE=balanced

# Enable fallback to Perplexity Sonar
RESEARCH_FALLBACK_ENABLED=true
PERPLEXITY_API_KEY=your_perplexity_api_key  # Only needed if fallback enabled
```

### 3. Verify Integration

Check the health endpoint:

```bash
curl http://localhost:8000/v1/health | python3 -m json.tool
```

You should see:
```json
{
  "status": "healthy",
  "services": {
    "perplexica": "healthy",
    "sonar": "healthy",
    "groq": "healthy"
  }
}
```

## 🔧 Configuration Options

### Focus Modes

Control what type of search Perplexica performs:

- `webSearch` (default) - General web search
- `academicSearch` - Academic papers and scholarly sources
- `writingAssistant` - Content writing and editing
- `wolframAlphaSearch` - Mathematical and computational queries
- `youtubeSearch` - YouTube video content
- `redditSearch` - Reddit discussions

```bash
PERPLEXICA_FOCUS_MODE=academicSearch
```

### Optimization Modes

Balance between speed and quality:

- `balanced` (default) - Good balance of speed and quality
- `speed` - Faster results with slightly lower quality

```bash
PERPLEXICA_OPTIMIZATION_MODE=speed
```

### Fallback Configuration

Control what happens when Perplexica fails:

```bash
# Enable/disable Perplexica entirely
PERPLEXICA_ENABLED=true

# Enable/disable fallback to Perplexity Sonar
RESEARCH_FALLBACK_ENABLED=true
```

## 📊 How It Works

### Research Flow

```
1. User submits fact-check request
2. Try Perplexica research (if PERPLEXICA_ENABLED=true)
   ├─ Success: Use Perplexica results
   └─ Failure: Fallback to Perplexity Sonar (if RESEARCH_FALLBACK_ENABLED=true)
3. Continue with LLM analysis using research context
4. Return fact-check results
```

### Provider Discovery

Perplexica automatically discovers available AI providers:

1. Calls `/api/providers` on initialization
2. Finds providers with chat models (Groq, OpenAI, etc.)
3. Finds providers with embedding models (Transformers, etc.)
4. **Smart model selection**: Prefers general-purpose models like:
   - `llama-3.3-70b-versatile`
   - `llama-3.1-8b-instant`
   - Over specialized models (guards, whisper, etc.)

### Error Handling

The integration handles these failure scenarios gracefully:

- **Connection errors** - Falls back to Perplexity Sonar
- **Timeouts** - Falls back to Perplexity Sonar
- **API errors** - Falls back to Perplexity Sonar
- **Both providers fail** - Continues fact-checking with limited research context

## 🔍 Troubleshooting

### Perplexica Not Connecting

**Symptom**: Logs show "Perplexica failed: Failed to connect to Perplexica"

**Solutions**:
1. Check Perplexica is running: `curl http://localhost:3000/api/providers`
2. Verify `PERPLEXICA_ENDPOINT` in `.env` matches your setup
3. If using Docker, ensure port 3000 is exposed

### No Chat Models Available

**Symptom**: Logs show "No chat models available from Perplexica provider"

**Solution**: This was fixed in the latest version. Update your code and restart:
```bash
git pull
# Restart backend server
```

### Requests Timing Out

**Symptom**: Perplexica requests timeout after 30 seconds

**Solutions**:
1. Increase timeout: `REQUEST_TIMEOUT=60` in `.env`
2. Use speed mode: `PERPLEXICA_OPTIMIZATION_MODE=speed`
3. Check Perplexica has sufficient resources (CPU/RAM)

### Check Logs

View backend logs to see which provider is being used:

```
INFO - Attempting research with Perplexica
INFO - Initialized Perplexica providers - Chat: groq-api (llama-3.3-70b-versatile), Embedding: Transformers (...)
INFO - Perplexica research successful. Found X citations
```

Or if fallback occurs:
```
WARNING - Perplexica failed: ..., attempting fallback
INFO - Falling back to Perplexity Sonar
INFO - Perplexity Sonar research successful. Found X citations
```

## 🎯 Disabling Perplexica

To revert to Perplexity Sonar only:

```bash
# Option 1: Disable Perplexica entirely
PERPLEXICA_ENABLED=false

# Option 2: Keep trying Perplexica but disable fallback
PERPLEXICA_ENABLED=true
RESEARCH_FALLBACK_ENABLED=false  # Will return error if Perplexica fails
```

Restart the server after changing environment variables.

## 📈 Performance

Typical response times:

- **Perplexica (local)**: 3-5 seconds
- **Perplexity Sonar (API)**: 2-4 seconds
- **Total fact-check**: 5-10 seconds (including LLM analysis)

## 🔐 Security Notes

- Perplexica runs locally, so all searches are private
- No data is sent to external services (unless fallback to Perplexity Sonar)
- API keys for Perplexity are only used if fallback is enabled and triggered
- Perplexica doesn't require an API key for localhost deployment

## 📚 Additional Resources

- [Perplexica GitHub](https://github.com/ItzCrazyKns/Perplexica)
- [Perplexica API Documentation](https://github.com/ItzCrazyKns/Perplexica/tree/master/docs/API)
- [FakeCheck Backend Documentation](./README.md)

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review backend logs for error messages
3. Test Perplexica directly: `curl http://localhost:3000/api/providers`
4. Open an issue on the FakeCheck repository
