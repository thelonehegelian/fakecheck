# 🚀 Railway Deployment Guide - FakeCheck & Perplexica

This guide outlines the step-by-step process for deploying the **FakeCheck Backend** and its primary research engine, **Perplexica**, on **Railway** with a production-grade, zero-fallback configuration.

---

## 🏗️ Architecture Overview

The deployed architecture consists of two main services running on Railway:
1. **FakeCheck Backend** (FastAPI): Exposes the fact-checking API, extracts claims, and runs final LLM analysis.
2. **Perplexica** (Next.js & Express): Performs local AI-powered web searches and gathers reliable citations.

```
                  ┌──────────────────────┐
                  │      User / Client   │
                  └──────────┬───────────┘
                             │ (https)
                             ▼
               ┌───────────────────────────┐
               │    FakeCheck Backend      │◄─── [LLM Providers (OpenRouter)]
               │ (FastAPI on Port 8000)    │
               └─────────────┬─────────────┘
                             │ (https)
                             ▼
               ┌───────────────────────────┐
               │        Perplexica         │◄─── [Local SearXNG / Web Search]
               │ (Next.js on Port 3000)    │
               └───────────────────────────┘
```

---

## 1. 🐍 Deploying the FakeCheck Backend

The backend is built from the FastAPI application and listens on port `8000` by default.

### 📋 Steps to Deploy
1. **Link your repository** to a new Railway Service.
2. Railway will automatically detect the `Dockerfile` and start building the container.
3. In the Railway dashboard, navigate to **Settings** -> **Public Networking**.
4. Set the **Service Port** to `8000` (which matches the port exposed by our `Dockerfile`).

### ⚙️ Required Environment Variables
Add the following variables in the **Variables** tab of the FakeCheck Backend service:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `DEPLOYMENT` | `hosted` | **Crucial:** Master switch that enables Perplexica-only research and bypasses Perplexity Sonar API key validation. |
| `LLM_PROVIDER` | `openrouter` | Specifies the LLM client (can also be `groq` or `anthropic`). |
| `OPENROUTER_API_KEY` | `sk-or-v1-xxxxxx...` | Your active API key for OpenRouter. |
| `OPENROUTER_MODEL` | `google/gemini-3.5-flash` | The model used for final fact-checking analysis. |
| `PERPLEXICA_ENDPOINT` | `https://<your-perplexica-domain>.up.railway.app` | The public or private URL of your deployed Perplexica service. |

---

## 2. 🔍 Deploying Perplexica

Perplexica serves as the primary search provider, enabling fact-checking queries without incurring external search API costs.

### 📋 Steps to Deploy
1. Deploy Perplexica (either via the [official Docker image](https://hub.docker.com/r/itzcrazykns1337/perplexica) or by linking the Perplexica source repository).
2. In the Railway dashboard under **Settings** -> **Public Networking**, set the **Service Port** to `3000` (as Perplexica's web engine listens on port `3000`).

### ⚙️ Required Environment Variables
To prevent connection timeouts and Loopback interface mismatch (IPv4 vs. IPv6) inside Railway, configure these exact environment variables in the **Variables** tab of the Perplexica service:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `PORT` | `3000` | Forces Next.js to bind strictly to port `3000`, matching your Railway public domain mapping. |
| `HOSTNAME` | `0.0.0.0` | **Crucial:** Forces Next.js to bind to all IPv4 interfaces. Without this, it binds to `localhost` (`::1` IPv6 loopback), which prevents the Railway load balancer (`127.0.0.1`) from connecting, resulting in a `502 Bad Gateway`. |

---

## 3. 🔗 Linking the Services

Once Perplexica is up and running healthy (accessing its domain serves the Perplexica home screen):
1. Copy Perplexica's public URL (e.g., `https://perplexica-production-a405.up.railway.app`).
2. Go to the **FakeCheck Backend** service -> **Variables** tab.
3. Set `PERPLEXICA_ENDPOINT` to your copied Perplexica URL.
4. Save and redeploy the backend.

---

## 4. ✅ Verification and Testing

You can verify that the system is fully operational and healthy by sending HTTP requests to the backend endpoints:

### Health Check Endpoint
Query the `/v1/health` endpoint:
```bash
curl https://<your-backend-domain>.up.railway.app/v1/health
```
**Expected Response (`200 OK`):**
```json
{
  "status": "healthy",
  "timestamp": "2026-05-30T18:55:56.155245",
  "version": "2.0.0",
  "services": {
    "perplexica": "healthy",
    "sonar": "disabled",
    "openrouter": "healthy",
    "source_credibility": "healthy",
    "claim_extraction": "healthy"
  }
}
```
*Note: `sonar` should show as `disabled` indicating the fallback was cleanly bypassed without causing startup crashes.*

### API Info Endpoint
Query the `/v1/info` endpoint to inspect active models and configurations:
```bash
curl https://<your-backend-domain>.up.railway.app/v1/info
```
**Expected Response (`200 OK`):**
Includes the loaded configurations, available model lists, and features.

---

## 💡 Troubleshooting

### 1. `502 Bad Gateway` on Perplexica Service
* **Symptom:** Next.js logs show it is ready and listening on port `3000`, but accessing the public URL returns a `502`.
* **Fix:** Double-check that `HOSTNAME` is set to `0.0.0.0` and `PORT` is set to `3000` under the Perplexica service environment variables.

### 2. `500 Internal Server Error` on Backend `/v1/info` or `/v1/health`
* **Symptom:** The global health check fails with `INTERNAL_ERROR`.
* **Fix:** Ensure `DEPLOYMENT` is set to `hosted` on the backend service. If it is omitted or set incorrectly, the backend will attempt to instantiate the Perplexity `SonarClient` using a missing key, which triggers an unhandled `OpenAIError`.
