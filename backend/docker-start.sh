#!/bin/bash

# FakeCheck Container Startup Script
# This script helps you quickly set up and start FakeCheck with Perplexica
# Supports both Docker and Podman

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}FakeCheck Container Setup${NC}"
echo -e "${GREEN}================================${NC}\n"

# Define which engine to use (Podman or Docker)
DOCKER_BIN=$(command -v podman || command -v docker)

# Check if a container engine is installed
if [ -z "$DOCKER_BIN" ]; then
    echo -e "${RED}Error: Neither Podman nor Docker is installed${NC}"
    echo "Please install either:"
    echo "  - Docker: https://docs.docker.com/get-docker/"
    echo "  - Podman: https://podman.io/getting-started/installation"
    exit 1
fi

# Detect the engine name for display
ENGINE_NAME=$(basename "$DOCKER_BIN")

# Check if compose is available
if [ "$ENGINE_NAME" = "podman" ]; then
    # Try podman-compose first, then podman compose
    if command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman-compose"
    elif podman compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="podman compose"
    else
        echo -e "${RED}Error: podman-compose is not available${NC}"
        echo "Please install podman-compose: pip install podman-compose"
        exit 1
    fi
else
    # Docker
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}Error: Docker Compose is not available${NC}"
        echo "Please install Docker Compose V2"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Using $ENGINE_NAME as container engine${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ No .env file found${NC}"
    echo -e "Creating .env from .env.example...\n"

    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env and add your API keys:${NC}"
        echo "  - GROQ_API_KEY (recommended) or ANTHROPIC_API_KEY"
        echo "  - PERPLEXITY_API_KEY (optional, for fallback)"
        echo ""
        read -p "Press Enter after you've configured your .env file..."
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file found${NC}"
fi

# Validate required environment variables
echo -e "\n${YELLOW}Validating configuration...${NC}"

# Source the .env file
set -a
source .env
set +a

# Check LLM provider configuration
if [ "$LLM_PROVIDER" = "groq" ]; then
    if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your_groq_api_key_here" ]; then
        echo -e "${RED}Error: GROQ_API_KEY is not configured${NC}"
        echo "Please set a valid GROQ_API_KEY in your .env file"
        exit 1
    fi
    echo -e "${GREEN}✓ Groq LLM provider configured${NC}"
elif [ "$LLM_PROVIDER" = "anthropic" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        echo -e "${RED}Error: ANTHROPIC_API_KEY is not configured${NC}"
        echo "Please set a valid ANTHROPIC_API_KEY in your .env file"
        exit 1
    fi
    echo -e "${GREEN}✓ Anthropic LLM provider configured${NC}"
else
    echo -e "${RED}Error: LLM_PROVIDER must be either 'groq' or 'anthropic'${NC}"
    exit 1
fi

# Check if research fallback is enabled
if [ "$RESEARCH_FALLBACK_ENABLED" = "true" ]; then
    if [ -z "$PERPLEXITY_API_KEY" ] || [ "$PERPLEXITY_API_KEY" = "your_perplexity_api_key_here" ]; then
        echo -e "${YELLOW}⚠ Research fallback is enabled but PERPLEXITY_API_KEY is not configured${NC}"
        echo "  The system will still work using Perplexica, but won't fall back if it fails"
    else
        echo -e "${GREEN}✓ Perplexity fallback configured${NC}"
    fi
fi

# Ask user what to do
echo -e "\n${YELLOW}What would you like to do?${NC}"
echo "1. Start services (build if needed)"
echo "2. Rebuild and start services"
echo "3. Stop services"
echo "4. View logs"
echo "5. Check service status"
echo "6. Exit"

read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo -e "\n${GREEN}Starting services...${NC}"
        $COMPOSE_CMD up -d
        ;;
    2)
        echo -e "\n${GREEN}Rebuilding and starting services...${NC}"
        $COMPOSE_CMD up -d --build
        ;;
    3)
        echo -e "\n${YELLOW}Stopping services...${NC}"
        $COMPOSE_CMD down
        echo -e "${GREEN}Services stopped${NC}"
        exit 0
        ;;
    4)
        echo -e "\n${GREEN}Showing logs (Ctrl+C to exit)...${NC}"
        $COMPOSE_CMD logs -f
        exit 0
        ;;
    5)
        echo -e "\n${GREEN}Service status:${NC}"
        $COMPOSE_CMD ps
        exit 0
        ;;
    6)
        echo -e "${GREEN}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
echo "This may take 1-2 minutes on first startup..."

# Function to check service health
check_health() {
    local service=$1
    local url=$2
    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service is healthy${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
        echo -n "."
    done

    echo -e "\n${RED}✗ $service failed to become healthy${NC}"
    return 1
}

# Check Perplexica health
echo -n "Checking Perplexica..."
if check_health "Perplexica" "http://localhost:3000"; then
    echo -e "${GREEN}Perplexica is ready at http://localhost:3000${NC}"
else
    echo -e "${YELLOW}⚠ Perplexica may not be ready yet${NC}"
    echo "Check logs with: $COMPOSE_CMD logs perplexica"
fi

# Check Backend health
echo -n "Checking Backend..."
if check_health "Backend" "http://localhost:8000/v1/health"; then
    echo -e "${GREEN}Backend is ready at http://localhost:8000${NC}"
else
    echo -e "${YELLOW}⚠ Backend may not be ready yet${NC}"
    echo "Check logs with: $COMPOSE_CMD logs backend"
fi

# Show final status
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Services Status${NC}"
echo -e "${GREEN}================================${NC}"
$COMPOSE_CMD ps

# Test the API
echo -e "\n${YELLOW}Testing the API...${NC}"
TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/check-fake \
    -H "Content-Type: application/json" \
    -d '{"text": "The Earth is flat."}' || echo "FAILED")

if [ "$TEST_RESPONSE" = "FAILED" ]; then
    echo -e "${RED}✗ API test failed${NC}"
    echo "Check logs with: $COMPOSE_CMD logs backend"
else
    echo -e "${GREEN}✓ API is working!${NC}"
fi

# Show useful information
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Quick Reference${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Backend API:    ${YELLOW}http://localhost:8000${NC}"
echo -e "API Docs:       ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "Perplexica UI:  ${YELLOW}http://localhost:3000${NC}"
echo -e "Health Check:   ${YELLOW}http://localhost:8000/v1/health${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:        $COMPOSE_CMD logs -f"
echo "  Stop services:    $COMPOSE_CMD down"
echo "  Restart:          $COMPOSE_CMD restart"
echo "  Rebuild:          $COMPOSE_CMD up -d --build"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}\n"
