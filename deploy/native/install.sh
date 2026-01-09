#!/bin/bash
# =============================================================================
# 7KT-AI Native Installation Script (Linux/Mac)
# Downloads Python locally - no system installation required
# =============================================================================

set -e

echo "=========================================="
echo "7KT-AI Native Installation"
echo "=========================================="

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)
echo "OS: $OS ($ARCH)"

# Save original directory
ORIGINAL_DIR="$(pwd)"

# Set install directory
INSTALL_DIR="$HOME/stt"

# =============================================================================
# Check basic prerequisites (Git, FFmpeg)
# =============================================================================
echo ""
echo "Checking prerequisites..."

MISSING=""

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
        echo "  brew install git ffmpeg node"
        echo ""
    elif [ "$OS" = "Linux" ]; then
        echo "Install on Ubuntu/Debian:"
        echo "  sudo apt update"
        echo "  sudo apt install git ffmpeg nodejs npm"
        echo ""
    fi

    echo "After installing, run this script again."
    exit 1
fi

echo ""
echo "All prerequisites OK!"

# =============================================================================
# Clone Repository
# =============================================================================
REPO_URL="https://github.com/hainguyen-keyti/stt.git"

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
# Download standalone Python (no system install required)
# =============================================================================
PYTHON_VERSION="3.11.9"
PYTHON_DIR="$INSTALL_DIR/.python"

if [ -f "$PYTHON_DIR/bin/python3" ]; then
    echo ""
    echo "Using existing Python installation..."
    PYTHON_BIN="$PYTHON_DIR/bin/python3"
else
    echo ""
    echo "Downloading Python $PYTHON_VERSION (standalone, local only)..."

    # Determine download URL based on OS and architecture
    if [ "$OS" = "Darwin" ]; then
        if [ "$ARCH" = "arm64" ]; then
            PYTHON_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240713/cpython-${PYTHON_VERSION}+20240713-aarch64-apple-darwin-install_only.tar.gz"
        else
            PYTHON_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240713/cpython-${PYTHON_VERSION}+20240713-x86_64-apple-darwin-install_only.tar.gz"
        fi
    elif [ "$OS" = "Linux" ]; then
        if [ "$ARCH" = "x86_64" ]; then
            PYTHON_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240713/cpython-${PYTHON_VERSION}+20240713-x86_64-unknown-linux-gnu-install_only.tar.gz"
        elif [ "$ARCH" = "aarch64" ]; then
            PYTHON_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240713/cpython-${PYTHON_VERSION}+20240713-aarch64-unknown-linux-gnu-install_only.tar.gz"
        fi
    fi

    if [ -z "$PYTHON_URL" ]; then
        echo "ERROR: Unsupported platform: $OS $ARCH"
        exit 1
    fi

    # Download and extract
    mkdir -p "$PYTHON_DIR"
    echo "Downloading from: $PYTHON_URL"
    curl -L "$PYTHON_URL" | tar xz -C "$PYTHON_DIR" --strip-components=1

    PYTHON_BIN="$PYTHON_DIR/bin/python3"
    echo "Python installed to: $PYTHON_DIR"
fi

echo "Python: $($PYTHON_BIN --version)"

# =============================================================================
# Create virtual environment with local Python
# =============================================================================
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip

# =============================================================================
# Detect hardware and install PyTorch
# =============================================================================
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

# =============================================================================
# Install dependencies
# =============================================================================
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

# =============================================================================
# Build frontend (optional)
# =============================================================================
if command -v npm &> /dev/null; then
    echo ""
    echo "Building frontend..."
    cd web && npm install && npm run build && cd ..
else
    echo ""
    echo "Skipping frontend build (Node.js not installed)"
fi

# =============================================================================
# Copy .env
# =============================================================================
if [ -f "$ORIGINAL_DIR/.env" ]; then
    cp "$ORIGINAL_DIR/.env" .env
    echo "Copied .env from $ORIGINAL_DIR"
elif [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
        echo "WARNING: Please edit .env to add your configuration"
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
echo "To uninstall completely, just delete:"
echo "  rm -rf $INSTALL_DIR"
echo ""
