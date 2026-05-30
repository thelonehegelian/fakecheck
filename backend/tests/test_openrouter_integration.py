import pytest
from unittest.mock import MagicMock, patch
from src.core.config import Settings
from src.services.llm_factory import LLMFactory
from src.services.openrouter_client import OpenRouterClient


def test_openrouter_factory_creation():
    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        openrouter_model="google/gemini-3.5-flash",
        perplexity_api_key="dummy"
    )
    client = LLMFactory.create_client(settings)
    assert isinstance(client, OpenRouterClient)
    assert client.api_key == "test-api-key"
    assert client.model == "google/gemini-3.5-flash"
    assert LLMFactory.get_model_name(settings) == "google/gemini-3.5-flash"


def test_openrouter_factory_creation_missing_key():
    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key=None,
        perplexity_api_key="dummy"
    )
    with pytest.raises(ValueError) as excinfo:
        LLMFactory.create_client(settings)
    assert "OPENROUTER_API_KEY is required" in str(excinfo.value)


def test_openrouter_default_model():
    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        perplexity_api_key="dummy"
    )
    client = LLMFactory.create_client(settings)
    assert client.model == "google/gemini-3.5-flash"
    assert LLMFactory.get_model_name(settings) == "google/gemini-3.5-flash"


@pytest.mark.asyncio
@patch("src.services.openrouter_client.OpenRouter")
async def test_openrouter_client_analyze_news(mock_openrouter_class):
    mock_client = MagicMock()
    mock_openrouter_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''{
            "fake_news_rating": 4,
            "fake_news_explanation": "This is false.",
            "true_news_explanation": "This might be true in another world.",
            "verification_steps": [
                {
                    "step": "Step 1",
                    "estimated_time": "1 min",
                    "complexity": "easy"
                }
            ],
            "confidence_score": 0.8,
            "risk_factors": ["unreliable source"]
        }'''))
    ]
    mock_client.chat.send.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        perplexity_api_key="dummy"
    )
    client = OpenRouterClient(settings)
    
    result = await client.analyze_news("claim text", "research info", [])
    
    assert result["fake_news_rating"] == 4
    assert result["fake_news_explanation"] == "This is false."
    assert result["model_used"] == "google/gemini-3.5-flash"


@pytest.mark.asyncio
@patch("src.services.openrouter_client.OpenRouter")
async def test_openrouter_client_analyze_source_credibility(mock_openrouter_class):
    mock_client = MagicMock()
    mock_openrouter_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''{
            "domain": "test.com",
            "name": "Test Site",
            "credibility_score": 90.0,
            "bias_rating": "center",
            "factual_accuracy": "high",
            "transparency_score": 85.0
        }'''))
    ]
    mock_client.chat.send.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        perplexity_api_key="dummy"
    )
    client = OpenRouterClient(settings)
    
    result = await client.analyze_source_credibility("some prompt", {})
    
    assert result["domain"] == "test.com"
    assert result["credibility_score"] == 90.0
    assert result["bias_rating"] == "center"


@pytest.mark.asyncio
@patch("src.services.openrouter_client.OpenRouter")
async def test_openrouter_client_extract_claims(mock_openrouter_class):
    mock_client = MagicMock()
    mock_openrouter_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''{
            "claims": [
                {
                    "claim": "Claim 1",
                    "claim_type": "factual",
                    "confidence": 0.9,
                    "context": "Context 1",
                    "verifiable": true
                }
            ],
            "summary": "Extracted 1 claim"
        }'''))
    ]
    mock_client.chat.send.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        perplexity_api_key="dummy"
    )
    client = OpenRouterClient(settings)
    
    result = await client.extract_claims("extract claims prompt", "some text")
    
    assert len(result["claims"]) == 1
    assert result["claims"][0]["claim"] == "Claim 1"
    assert result["summary"] == "Extracted 1 claim"


@pytest.mark.asyncio
@patch("src.services.openrouter_client.OpenRouter")
async def test_openrouter_client_analyze_claim_verifiability(mock_openrouter_class):
    mock_client = MagicMock()
    mock_openrouter_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='''{
            "verification_methods": ["Method A"],
            "potential_sources": ["Source A"],
            "difficulty_level": "easy",
            "time_estimate": "5 min",
            "key_terms": ["term A"],
            "searchability_score": 0.95
        }'''))
    ]
    mock_client.chat.send.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        perplexity_api_key="dummy"
    )
    client = OpenRouterClient(settings)
    
    result = await client.analyze_claim_verifiability("some prompt", "some claim")
    
    assert result["difficulty_level"] == "easy"
    assert result["searchability_score"] == 0.95


@pytest.mark.asyncio
@patch("src.services.openrouter_client.OpenRouter")
async def test_openrouter_client_health_check(mock_openrouter_class):
    mock_client = MagicMock()
    mock_openrouter_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="OK"))
    ]
    mock_client.chat.send.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="test-api-key",
        perplexity_api_key="dummy"
    )
    client = OpenRouterClient(settings)
    
    health = await client.health_check()
    assert health["status"] == "healthy"
