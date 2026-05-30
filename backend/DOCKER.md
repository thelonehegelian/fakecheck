# Docker Deployment Guide

This guide covers deploying FakeCheck backend with Perplexica using Docker.

## Quick Start

### Prerequisites

- Docker Engine 20.10+ and Docker Compose V2
- At least 4GB of available RAM
- API keys (see Configuration section)

### 1. Clone and Setup

```bash
cd backend

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

### 2. Configure Environment

At minimum, you need to set one of these LLM providers in your `.env`:

**Option A: Using Groq (Recommended - Fast & Free)**
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

**Option B: Using Anthropic Claude**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

**Research Fallback (Optional)**

If Perplexica fails, the system can fall back to Perplexity Sonar:
```env
RESEARCH_FALLBACK_ENABLED=true
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 4. Verify Deployment

Once services are running, verify they're working:

```bash
# Check backend health
curl http://localhost:8000/v1/health

# Check Perplexica (should show web interface)
curl http://localhost:3000

# Test fact-checking endpoint
curl -X POST http://localhost:8000/v1/check-fake \
  -H "Content-Type: application/json" \
  -d '{"text": "The Earth is flat."}'
```

## Architecture

The Docker setup includes two main services:

### 1. Perplexica (Port 3000)
- **Image**: `itzcrazykns1337/perplexica:latest`
- **Purpose**: AI-powered research engine with integrated SearxNG
- **Features**: Web search, academic papers, YouTube, Reddit, Wolfram Alpha
- **Data**: Persisted in `perplexica-data` and `perplexica-uploads` volumes

### 2. FakeCheck Backend (Port 8000)
- **Built from**: `backend/Dockerfile`
- **Purpose**: FastAPI-based fact-checking API
- **Dependencies**: Connects to Perplexica for research
- **Data**: Persisted in `backend-data` and `backend-logs` volumes

### Network Configuration

Services communicate via the `fakecheck-network` bridge network:
- Backend → Perplexica: `http://perplexica:3000` (internal)
- External access:
  - Backend: `http://localhost:8000`
  - Perplexica: `http://localhost:3000`

## Configuration

### Environment Variables

The `.env` file supports the following configuration options:

#### LLM Provider Selection
```env
LLM_PROVIDER=groq              # groq or anthropic
GROQ_API_KEY=<your-key>        # If using Groq
ANTHROPIC_API_KEY=<your-key>   # If using Anthropic
```

#### Perplexica Configuration
```env
PERPLEXICA_ENABLED=true                    # Enable/disable Perplexica
PERPLEXICA_ENDPOINT=http://perplexica:3000 # Auto-configured in Docker
PERPLEXICA_FOCUS_MODE=webSearch            # Search mode
PERPLEXICA_OPTIMIZATION_MODE=balanced      # speed or balanced
```

#### Research Fallback
```env
RESEARCH_FALLBACK_ENABLED=true             # Enable Perplexity fallback
PERPLEXITY_API_KEY=<your-key>              # Only if fallback enabled
```

#### API Configuration
```env
MAX_TOKENS=4000                # AI response token limit
REQUEST_TIMEOUT=30             # Request timeout (seconds)
RATE_LIMIT_PER_MINUTE=100      # API rate limit
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
```

### Docker Compose Customization

#### Production Mode

For production, disable source code mounting in `docker-compose.yml`:

```yaml
services:
  backend:
    volumes:
      # Comment out these development mounts:
      # - ./src:/app/src
      # - ./main.py:/app/main.py

      # Keep only data volumes:
      - backend-data:/app/data
      - backend-logs:/app/logs
```

#### Custom Ports

To change exposed ports:

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # Expose backend on port 8080

  perplexica:
    ports:
      - "3001:3000"  # Expose Perplexica on port 3001
```

#### Resource Limits

Add resource constraints for production:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Management

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs -f perplexica

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec perplexica sh

# Rebuild after code changes
docker-compose up -d --build

# Remove everything including volumes
docker-compose down -v
```

### Monitoring

Check service health:

```bash
# Check all services
docker-compose ps

# Detailed backend health
curl http://localhost:8000/v1/health | jq

# Detailed info
curl http://localhost:8000/v1/info | jq

# View real-time logs
docker-compose logs -f --tail=100
```

### Troubleshooting

#### Backend can't connect to Perplexica

Check if Perplexica is healthy:
```bash
docker-compose ps perplexica
docker-compose logs perplexica
```

Verify network connectivity:
```bash
docker-compose exec backend ping -c 3 perplexica
docker-compose exec backend curl http://perplexica:3000
```

#### Perplexica not starting

Increase startup time in health check:
```yaml
healthcheck:
  start_period: 120s  # Increase from 60s
```

Check Perplexica logs:
```bash
docker-compose logs perplexica | grep -i error
```

#### Out of Memory

Perplexica with SearxNG needs ~2GB RAM. Increase Docker memory:
- Docker Desktop: Settings → Resources → Memory → 6GB+
- Linux: No limit by default, check `free -h`

#### Permission Issues

Fix volume permissions:
```bash
docker-compose down
docker volume rm backend_backend-data backend_backend-logs
docker-compose up -d
```

## API Usage

### Health Check

```bash
curl http://localhost:8000/v1/health
```

Response:
```json
{
  "status": "healthy",
  "dependencies": {
    "perplexica": "healthy",
    "perplexity": "healthy",
    "llm_provider": "healthy"
  }
}
```

### Fact-Check Endpoint

```bash
curl -X POST http://localhost:8000/v1/check-fake \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Breaking: Scientists discover that the moon is made of cheese."
  }' | jq
```

Response:
```json
{
  "rating": 1,
  "rating_label": "Completely False",
  "fake_explanation": "This claim is entirely fabricated...",
  "true_explanation": "The moon is composed of rock and regolith...",
  "verification_steps": [...],
  "processing_time_seconds": 3.45,
  "research_sources": [...]
}
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/v1/check-fake/batch \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"text": "Claim 1"},
      {"text": "Claim 2"}
    ],
    "parallel": true
  }' | jq
```

## Data Persistence

### Volumes

Docker Compose creates four persistent volumes:

| Volume | Purpose | Path in Container |
|--------|---------|-------------------|
| `perplexica-data` | Perplexica configuration | `/home/perplexica/data` |
| `perplexica-uploads` | User uploads | `/home/perplexica/uploads` |
| `backend-data` | Backend data | `/app/data` |
| `backend-logs` | Application logs | `/app/logs` |

### Backup

```bash
# Backup all volumes
docker run --rm \
  -v backend_backend-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/backend-data.tar.gz -C /data .

# Restore
docker run --rm \
  -v backend_backend-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/backend-data.tar.gz -C /data
```

## Updating

### Update Images

```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d

# Remove old images
docker image prune -f
```

### Update Backend Code

If you've made code changes:

```bash
# Rebuild and restart
docker-compose up -d --build backend

# Or force full rebuild
docker-compose build --no-cache backend
docker-compose up -d backend
```

## Security

### Production Checklist

- [ ] Change default ports if needed
- [ ] Set strong `CORS_ORIGINS` in `.env`
- [ ] Use environment-specific `.env` files
- [ ] Enable HTTPS via reverse proxy (nginx/traefik)
- [ ] Set `DEBUG=false` in production
- [ ] Configure rate limiting
- [ ] Regular security updates: `docker-compose pull`
- [ ] Monitor logs: `docker-compose logs -f`
- [ ] Backup volumes regularly

### Reverse Proxy Example (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Development

### Hot Reload

The docker-compose.yml mounts source code by default for development:

```yaml
volumes:
  - ./src:/app/src
  - ./main.py:/app/main.py
```

Changes to Python files will trigger uvicorn's auto-reload.

### Running Tests

```bash
# Install test dependencies in container
docker-compose exec backend pip install pytest pytest-asyncio httpx

# Run tests
docker-compose exec backend pytest tests/ -v

# Run specific test suite
docker-compose exec backend pytest tests/test_integration_live.py -v
```

### Debugging

```bash
# Interactive Python shell
docker-compose exec backend python

# Check environment variables
docker-compose exec backend env | grep -E "(GROQ|ANTHROPIC|PERPLEXICA)"

# Test Perplexica connectivity
docker-compose exec backend curl http://perplexica:3000/api/providers
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourorg/fake-check/issues
- Documentation: See README.md, TESTING.md, PERPLEXICA_INTEGRATION.md

## License

See LICENSE file in repository root.
