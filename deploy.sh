#!/bin/bash

# STT Service Deploy Script
# Usage: ./deploy.sh

set -e

echo "=== Pulling latest code ==="
git pull origin master

echo "=== Building Docker image ==="
docker build -t stt-service .

echo "=== Stopping old container ==="
docker stop stt-service 2>/dev/null || true
docker rm stt-service 2>/dev/null || true

echo "=== Starting new container ==="
docker run -d -p 8000:8000 \
  -v whisper-cache:/root/.cache/whisper \
  -v hf-cache:/root/.cache/huggingface \
  --name stt-service \
  --restart unless-stopped \
  stt-service

echo "=== Cleanup old images ==="
docker image prune -f

echo "=== Done! ==="
echo "Web UI: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
