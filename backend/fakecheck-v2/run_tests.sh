#!/bin/bash

# Script to run the fake news API tests
# Make sure to set your environment variables before running

echo "🧪 Running Fake News API Integration Tests"
echo "=========================================="

# Check if required environment variables are set
if [ -z "$PERPLEXITY_API_KEY" ]; then
    echo "❌ Error: PERPLEXITY_API_KEY environment variable is not set"
    echo "Please set it with: export PERPLEXITY_API_KEY='your_key_here'"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable is not set" 
    echo "Please set it with: export ANTHROPIC_API_KEY='your_key_here'"
    exit 1
fi

echo "✅ Environment variables are set"
echo "📦 Installing dependencies..."

# Install dependencies with uv
uv sync

echo "🚀 Running tests..."
echo ""

# Run the tests with verbose output using uv
uv run pytest test_fake_news_api.py -v -s

echo ""
echo "✨ Test run complete!"