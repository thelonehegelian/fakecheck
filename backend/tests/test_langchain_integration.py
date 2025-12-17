"""
Unit tests for LangChain integration using mocks.
These tests verify that the clients interact correctly with LangChain components.
"""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Set dummy environment variables BEFORE importing modules that instantiate Settings
os.environ["ANTHROPIC_API_KEY"] = "dummy"
os.environ["PERPLEXITY_API_KEY"] = "dummy"

from src.core.config import Settings
from src.services.anthropic_client import AnthropicClient
from src.services.sonar_client import SonarClient
from src.models.responses import FactCheckResponse, SourceCredibility

@pytest.fixture
def mock_settings():
    return Settings(
        ANTHROPIC_API_KEY="test_key",
        PERPLEXITY_API_KEY="test_key",
        anthropic_model="claude-3-test",
        perplexity_model="sonar-test"
    )

@pytest.fixture
def mock_anthropic_chain():
    mock_llm = AsyncMock()
    mock_structured_llm = AsyncMock()
    mock_chain = AsyncMock()
    
    # Setup chain behavior
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    # We patch the chain construction in the client methods
    return mock_chain

@pytest.mark.asyncio
async def test_anthropic_client_analyze_news(mock_settings):
    """Test AnthropicClient.analyze_news with mocks."""
    client = AnthropicClient(mock_settings)
    
    # Mock the LLM and chain
    with patch("src.services.anthropic_client.ChatAnthropic") as MockChatAnthropic, \
         patch("src.services.anthropic_client.ChatPromptTemplate") as MockPrompt:
        
        # Setup mock instance
        mock_llm_instance = MockChatAnthropic.return_value
        mock_structured_llm = AsyncMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        
        # Setup chain
        mock_chain = AsyncMock()
        # Simulate pipe operator behavior: prompt | structured_llm -> chain
        MockPrompt.from_messages.return_value.__or__.return_value = mock_chain
        
        # Mock structured response
        mock_response = FactCheckResponse(
            fake_news_rating=1,
            fake_news_explanation="True",
            true_news_explanation="True",
            verification_steps=[],
            citations=["source1"],
            processing_time_ms=100
        )
        mock_chain.ainvoke.return_value = mock_response
        
        # Call the method
        result = await client.analyze_news(
            news_text="Test news",
            research_context="Context",
            citations=["source1"]
        )
        
        # Verify
        assert result["fake_news_rating"] == 1
        assert result["model_used"] == "claude-3-test"
        mock_chain.ainvoke.assert_called_once()
        args = mock_chain.ainvoke.call_args[0][0]
        assert args["news_text"] == "Test news"
        assert args["research_context"] == "Context"

@pytest.mark.asyncio
async def test_sonar_client_research_claim(mock_settings):
    """Test SonarClient.research_claim with mocks."""
    client = SonarClient(mock_settings)
    
    # Mock the LLM
    with patch("src.services.sonar_client.ChatOpenAI") as MockChatOpenAI, \
         patch("src.services.sonar_client.SystemMessage") as MockSystemMsg, \
         patch("src.services.sonar_client.HumanMessage") as MockHumanMsg:
        
        # Ensure the client instance uses a mock, or rely on the one created in __init__
        # Since __init__ runs before we patch context if we instantiate inside, 
        # we might need to rely on the patch being active during init OR patch the instance attribute.
        # But here we instantiate client before patch context starts? No, instantiate inside or mock the class used in init.
        pass

    # Re-instantiate inside patch
    with patch("src.services.sonar_client.ChatOpenAI") as MockChatOpenAI:
        mock_llm_instance = MockChatOpenAI.return_value
        client = SonarClient(mock_settings) # Now verify it uses the mock
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = "Research content"
        mock_response.response_metadata = {
            "citations": ["http://example.com"],
            "model": "sonar-test-response",
            "token_usage": {"total_tokens": 10}
        }
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        
        # Call the method
        result = await client.research_claim("Test claim")
        
        # Verify
        assert result["content"] == "Research content"
        assert result["citations"] == ["http://example.com"]
        assert result["model_used"] == "sonar-test-response"
        mock_llm_instance.ainvoke.assert_called_once()

