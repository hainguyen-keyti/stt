# =============================================================================
# Multi-stage Dockerfile for STT Service
# Supports: CPU, NVIDIA CUDA GPU
# Auto-detects hardware at runtime for optimal performance
# =============================================================================

# Build argument for target platform (cpu or gpu)
ARG TARGET_PLATFORM=cpu

# =============================================================================
# Stage 1: Build frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# =============================================================================
# Stage 2a: Python API (CPU version)
# =============================================================================
FROM python:3.11-slim AS cpu-base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

# Install PyTorch CPU version
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install ASR engines
RUN pip3 install --no-cache-dir faster-whisper openai-whisper

# Install TTS engines
RUN pip3 install --no-cache-dir edge-tts gTTS pydub

# Install audio separator (CPU version)
RUN pip3 install --no-cache-dir "audio-separator[cpu]" soundfile

# =============================================================================
# Stage 2b: Python API (GPU/CUDA version)
# =============================================================================
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04 AS gpu-base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ffmpeg \
    git \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

# Install PyTorch with CUDA support
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install other dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install ASR engines
RUN pip3 install --no-cache-dir faster-whisper openai-whisper

# Install TTS engines
RUN pip3 install --no-cache-dir edge-tts gTTS pydub

# Install audio separator (GPU version)
RUN pip3 install --no-cache-dir "audio-separator[gpu]" soundfile

# =============================================================================
# Stage 3: Final image (selects based on TARGET_PLATFORM)
# =============================================================================
FROM ${TARGET_PLATFORM}-base AS final

# Copy application code
COPY api/ ./api/
COPY modules/ ./modules/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/web/dist ./web/dist

# Create directories for uploads and cache
RUN mkdir -p /app/uploads /app/cache /root/.cache/whisper /root/.cache/huggingface /root/.cache/torch

# Environment variables for optimal performance
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV WHISPER_CACHE_DIR=/root/.cache/whisper
ENV HF_HOME=/root/.cache/huggingface

# PyTorch optimizations
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with optimal settings
# - workers: auto-scaled based on CPU cores (set via env or docker-compose)
# - timeout: increased for large model loading
CMD ["python3", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]
