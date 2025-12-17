#!/bin/bash

echo "Testing Health Endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "\n\nTesting Info Endpoint..."
curl -s http://localhost:8000/v1/info | python3 -m json.tool

echo -e "\n\nTesting Fact Check (Simple)..."
curl -s -X POST http://localhost:8000/v1/check-fake \
  -H "Content-Type: application/json" \
  -d '{"news": "The earth is flat and the moon is made of cheese.", "priority": "normal"}' | python3 -m json.tool
