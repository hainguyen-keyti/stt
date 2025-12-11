# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Python API (CPU version)
FROM python:3.11-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

# Install PyTorch CPU version
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install ASR engines
RUN pip3 install --no-cache-dir faster-whisper openai-whisper

# Copy application code
COPY api/ ./api/
COPY lib/ ./lib/
COPY presets/ ./presets/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/web/dist ./web/dist

# Create directories for uploads and cache
RUN mkdir -p /app/uploads /app/cache /root/.cache/whisper /root/.cache/huggingface

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV WHISPER_CACHE_DIR=/root/.cache/whisper
ENV HF_HOME=/root/.cache/huggingface

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python3", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
