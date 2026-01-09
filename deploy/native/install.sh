#!/bin/bash
# =============================================================================
# 7KT-AI Native Installation Script (Linux/Mac)
# Auto-detects hardware and installs optimal dependencies
# =============================================================================

set -e

echo "=========================================="
echo "7KT-AI Native Installation"
echo "=========================================="

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)
echo "OS: $OS ($ARCH)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed"
    echo "Please install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PYTHON_VERSION"

# Check if Python version >= 3.10
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python 3.10+ is required (found $PYTHON_VERSION)"
    exit 1
fi

# Clone or update repository
REPO_URL="https://github.com/hainguyen-keyti/stt.git"
INSTALL_DIR="$HOME/stt"

if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Detect hardware and install PyTorch
echo ""
echo "Detecting hardware..."

if [ "$OS" = "Darwin" ]; then
    # macOS
    if [ "$ARCH" = "arm64" ]; then
        echo "Apple Silicon (M1/M2/M3/M4) detected - Installing PyTorch with MPS support"
        pip install torch torchvision torchaudio
    else
        echo "Intel Mac detected - Installing PyTorch CPU"
        pip install torch torchvision torchaudio
    fi
elif [ "$OS" = "Linux" ]; then
    # Linux - Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        echo "NVIDIA GPU detected - Installing PyTorch with CUDA"
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    elif [ -d "/opt/rocm" ]; then
        echo "AMD ROCm detected - Installing PyTorch with ROCm"
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6
    else
        echo "No GPU detected - Installing PyTorch CPU"
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
fi

# Install requirements
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Install ASR engines
echo "Installing ASR engines..."
pip install faster-whisper openai-whisper

# Install TTS engines
echo "Installing TTS engines..."
pip install edge-tts gTTS pydub

# Install audio separator
echo "Installing audio separator..."
if command -v nvidia-smi &> /dev/null; then
    pip install "audio-separator[gpu]" soundfile
else
    pip install "audio-separator[cpu]" soundfile
fi

# Build frontend
echo ""
echo "Building frontend..."
if command -v npm &> /dev/null; then
    cd web
    npm install
    npm run build
    cd ..
else
    echo "WARNING: npm not found, skipping frontend build"
    echo "Install Node.js from https://nodejs.org/ if you need the web UI"
fi

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env 2>/dev/null || echo "# Add your configuration here" > .env
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  cd $INSTALL_DIR"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"
echo ""
