#!/bin/bash
# =============================================================================
# 7KT-AI Quick Start Script
# Auto-detects hardware and runs with optimal configuration
# =============================================================================

set -e

echo "=========================================="
echo "7KT-AI Service Launcher"
echo "=========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running"
    echo "Please start Docker Desktop or Docker service"
    exit 1
fi

# Pull latest image
echo "Pulling latest image..."
docker pull keytikontum/7kt-ai:latest

# Check for NVIDIA GPU
GPU_ARGS=""
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected!"
    GPU_ARGS="--gpus all"
    echo "Running with GPU acceleration"
else
    echo "No NVIDIA GPU detected, running on CPU"
fi

# Stop existing container
echo "Stopping existing container (if any)..."
docker stop 7kt-ai 2>/dev/null || true
docker rm 7kt-ai 2>/dev/null || true

# Run container
echo "Starting container..."
docker run -d \
    --name 7kt-ai \
    -p 8000:8000 \
    -v whisper-cache:/root/.cache/whisper \
    -v hf-cache:/root/.cache/huggingface \
    -v torch-cache:/root/.cache/torch \
    --restart unless-stopped \
    $GPU_ARGS \
    keytikontum/7kt-ai:latest

echo ""
echo "=========================================="
echo "7KT-AI is starting..."
echo "=========================================="
echo ""
echo "Web UI:    http://localhost:8000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
echo "View logs: docker logs -f 7kt-ai"
echo "Stop:      docker stop 7kt-ai"
echo ""
