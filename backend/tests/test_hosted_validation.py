import pytest
import sys
from unittest.mock import patch
from fastapi import FastAPI

# Import settings, Settings class, and lifespan/app components
from src.core.config import get_settings, Settings
from main import create_app

def test_pydantic_simplification_resolves_automatically():
    """Test that setting DEPLOYMENT=hosted automatically configures perplexica and fallback correctly at the Pydantic level."""
    # When DEPLOYMENT is hosted, perplexica should be True and fallback should be False
    settings = Settings(deployment="hosted")
    assert settings.perplexica_enabled is True
    assert settings.research_fallback_enabled is False

    # When DEPLOYMENT is not hosted or not set, they should preserve their standard defaults
    settings_default = Settings(deployment="local")
    assert settings_default.perplexica_enabled is True
    assert settings_default.research_fallback_enabled is True


@pytest.mark.asyncio
async def test_hosted_deployment_success():
    """Test that the application starts successfully when DEPLOYMENT=hosted, perplexica is enabled, and fallback is disabled."""
    settings = get_settings()
    
    # Save original settings
    orig_deployment = settings.deployment
    orig_perplexica = settings.perplexica_enabled
    orig_fallback = settings.research_fallback_enabled
    
    try:
        # Configure settings for a valid hosted environment
        settings.deployment = "hosted"
        settings.perplexica_enabled = True
        settings.research_fallback_enabled = False
        
        # Re-create app to use our updated settings
        app = create_app()
        
        # Test starting the app via the router lifespan context
        async with app.router.lifespan_context(app):
            pass
            
    finally:
        # Restore original settings
        settings.deployment = orig_deployment
        settings.perplexica_enabled = orig_perplexica
        settings.research_fallback_enabled = orig_fallback


@pytest.mark.asyncio
async def test_hosted_deployment_fails_when_perplexica_disabled():
    """Test that the application crashes on startup if DEPLOYMENT=hosted but perplexica is disabled."""
    settings = get_settings()
    
    # Save original settings
    orig_deployment = settings.deployment
    orig_perplexica = settings.perplexica_enabled
    orig_fallback = settings.research_fallback_enabled
    
    try:
        # Configure settings incorrectly for hosted environment
        settings.deployment = "hosted"
        settings.perplexica_enabled = False
        settings.research_fallback_enabled = False
        
        app = create_app()
        
        # Attempting to start the lifespan should raise SystemExit due to sys.exit(1)
        with pytest.raises(SystemExit) as exc_info:
            async with app.router.lifespan_context(app):
                pass
                
        assert exc_info.value.code == 1
        
    finally:
        # Restore original settings
        settings.deployment = orig_deployment
        settings.perplexica_enabled = orig_perplexica
        settings.research_fallback_enabled = orig_fallback


@pytest.mark.asyncio
async def test_hosted_deployment_fails_when_fallback_enabled():
    """Test that the application crashes on startup if DEPLOYMENT=hosted but fallback is enabled."""
    settings = get_settings()
    
    # Save original settings
    orig_deployment = settings.deployment
    orig_perplexica = settings.perplexica_enabled
    orig_fallback = settings.research_fallback_enabled
    
    try:
        # Configure settings incorrectly for hosted environment
        settings.deployment = "hosted"
        settings.perplexica_enabled = True
        settings.research_fallback_enabled = True
        
        app = create_app()
        
        # Attempting to start the lifespan should raise SystemExit due to sys.exit(1)
        with pytest.raises(SystemExit) as exc_info:
            async with app.router.lifespan_context(app):
                pass
                
        assert exc_info.value.code == 1
        
    finally:
        # Restore original settings
        settings.deployment = orig_deployment
        settings.perplexica_enabled = orig_perplexica
        settings.research_fallback_enabled = orig_fallback
