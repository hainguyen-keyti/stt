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

# =============================================================================
# Check Prerequisites
# =============================================================================
echo ""
echo "Checking prerequisites..."

MISSING=""

# Check Python 3.10+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        echo "[X] Python: $PYTHON_VERSION (need 3.10+)"
        MISSING="$MISSING python"
    else
        echo "[OK] Python: $PYTHON_VERSION"
    fi
else
    echo "[X] Python: not found"
    MISSING="$MISSING python"
fi

# Check Git
if command -v git &> /dev/null; then
    echo "[OK] Git: $(git --version | cut -d' ' -f3)"
else
    echo "[X] Git: not found"
    MISSING="$MISSING git"
fi

# Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "[OK] FFmpeg: installed"
else
    echo "[X] FFmpeg: not found"
    MISSING="$MISSING ffmpeg"
fi

# Check Node.js (optional)
if command -v npm &> /dev/null; then
    echo "[OK] Node.js: $(node --version 2>/dev/null || echo 'installed')"
else
    echo "[!] Node.js: not found (optional, for web UI)"
fi

# If missing prerequisites, show install instructions
if [ -n "$MISSING" ]; then
    echo ""
    echo "=========================================="
    echo "Missing prerequisites:$MISSING"
    echo "=========================================="
    echo ""

    if [ "$OS" = "Darwin" ]; then
        echo "Install on macOS with Homebrew:"
        echo ""
        if ! command -v brew &> /dev/null; then
            echo "  # First install Homebrew:"
            echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            echo ""
        fi
        echo "  brew install python@3.11 git ffmpeg node"
        echo ""
    elif [ "$OS" = "Linux" ]; then
        echo "Install on Ubuntu/Debian:"
        echo "  sudo apt update"
        echo "  sudo apt install python3.11 python3.11-venv git ffmpeg nodejs npm"
        echo ""
        echo "Install on CentOS/RHEL:"
        echo "  sudo yum install python3.11 git ffmpeg nodejs npm"
        echo ""
    fi

    echo "After installing, run this script again:"
    echo '  curl -fsSL https://raw.githubusercontent.com/hainguyen-keyti/stt/master/deploy/native/install.sh | bash'
    exit 1
fi

echo ""
echo "All prerequisites OK!"

# =============================================================================
# Clone Repository
# =============================================================================
REPO_URL="https://github.com/hainguyen-keyti/stt.git"
INSTALL_DIR="$HOME/stt"

echo ""
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# =============================================================================
# Installation
# =============================================================================

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo ""
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
echo ""
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
    echo ""
    echo "Building frontend..."
    cd web && npm install && npm run build && cd ..
else
    echo ""
    echo "Skipping frontend build (Node.js not installed)"
fi

# Create .env if not exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
    fi
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
echo "Web UI:   http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
