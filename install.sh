#!/bin/bash
# =============================================================================
# 7KT-AI Quick Install Script
# Run from source directory
# =============================================================================

set -e

echo "=========================================="
echo "7KT-AI Installation"
echo "=========================================="

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)
echo "OS: $OS ($ARCH)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "Python: $PYTHON_VERSION"

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip

# Detect hardware and install PyTorch
echo ""
echo "Detecting hardware..."

if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    echo "Apple Silicon detected - Installing PyTorch with MPS"
    pip install torch torchvision torchaudio
elif command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected - Installing PyTorch with CUDA"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    echo "No GPU detected - Installing PyTorch CPU"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install faster-whisper openai-whisper
pip install edge-tts gTTS pydub

# Audio separator
if command -v nvidia-smi &> /dev/null; then
    pip install "audio-separator[gpu]" soundfile
else
    pip install "audio-separator[cpu]" soundfile
fi

# Build frontend
if command -v npm &> /dev/null; then
    echo "Building frontend..."
    cd web && npm install && npm run build && cd ..
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "To start: ./start.sh"
echo ""
