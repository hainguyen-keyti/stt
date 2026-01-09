#!/bin/bash
# =============================================================================
# 7KT-AI Native Installation Script (Linux/Mac)
# Downloads everything locally - no system installation required
# =============================================================================

set -e

echo "=========================================="
echo "7KT-AI Native Installation"
echo "=========================================="

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)
echo "OS: $OS ($ARCH)"

# Install directory = current directory
INSTALL_DIR="$(pwd)"
TOOLS_DIR="$INSTALL_DIR/.tools"

# Create tools directory
mkdir -p "$TOOLS_DIR"

# =============================================================================
# Download Git (portable) if not available
# =============================================================================
download_git() {
    if [ "$OS" = "Darwin" ]; then
        # macOS - Git comes with Xcode Command Line Tools, prompt to install
        echo "Git not found. Installing Xcode Command Line Tools..."
        xcode-select --install 2>/dev/null || true
        echo "Please complete the installation dialog, then run this script again."
        exit 1
    elif [ "$OS" = "Linux" ]; then
        # Linux - download portable git
        echo "Downloading portable Git..."
        GIT_VERSION="2.43.0"
        if [ "$ARCH" = "x86_64" ]; then
            GIT_URL="https://github.com/git/git/archive/refs/tags/v${GIT_VERSION}.tar.gz"
        fi
        # For Linux, git is usually available or easy to install
        echo "Please install git using your package manager:"
        echo "  Ubuntu/Debian: sudo apt install git"
        echo "  CentOS/RHEL: sudo yum install git"
        exit 1
    fi
}

# =============================================================================
# Download FFmpeg (portable)
# =============================================================================
download_ffmpeg() {
    FFMPEG_DIR="$TOOLS_DIR/ffmpeg"

    if [ -f "$FFMPEG_DIR/ffmpeg" ]; then
        echo "[OK] FFmpeg: already downloaded"
        return
    fi

    echo "Downloading FFmpeg (portable)..."
    mkdir -p "$FFMPEG_DIR"

    if [ "$OS" = "Darwin" ]; then
        if [ "$ARCH" = "arm64" ]; then
            FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
            FFPROBE_URL="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
        else
            FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
            FFPROBE_URL="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
        fi

        # Download ffmpeg
        curl -L "$FFMPEG_URL" -o "$FFMPEG_DIR/ffmpeg.zip"
        unzip -o "$FFMPEG_DIR/ffmpeg.zip" -d "$FFMPEG_DIR"
        rm "$FFMPEG_DIR/ffmpeg.zip"

        # Download ffprobe
        curl -L "$FFPROBE_URL" -o "$FFMPEG_DIR/ffprobe.zip"
        unzip -o "$FFMPEG_DIR/ffprobe.zip" -d "$FFMPEG_DIR"
        rm "$FFMPEG_DIR/ffprobe.zip"

        chmod +x "$FFMPEG_DIR/ffmpeg" "$FFMPEG_DIR/ffprobe"

    elif [ "$OS" = "Linux" ]; then
        if [ "$ARCH" = "x86_64" ]; then
            FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        elif [ "$ARCH" = "aarch64" ]; then
            FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
        fi

        curl -L "$FFMPEG_URL" | tar xJ -C "$FFMPEG_DIR" --strip-components=1
    fi

    echo "FFmpeg installed to: $FFMPEG_DIR"
}

# =============================================================================
# Download Python (standalone)
# =============================================================================
download_python() {
    PYTHON_VERSION="3.11.9"
    PYTHON_DIR="$TOOLS_DIR/python"

    if [ -f "$PYTHON_DIR/bin/python3" ]; then
        echo "[OK] Python: already downloaded"
        PYTHON_BIN="$PYTHON_DIR/bin/python3"
        return
    fi

    echo "Downloading Python $PYTHON_VERSION (standalone)..."
    mkdir -p "$PYTHON_DIR"

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

    curl -L "$PYTHON_URL" | tar xz -C "$PYTHON_DIR" --strip-components=1
    PYTHON_BIN="$PYTHON_DIR/bin/python3"
    echo "Python installed to: $PYTHON_DIR"
}

# =============================================================================
# Check/Download tools
# =============================================================================
echo ""
echo "Checking/downloading tools..."

# Check Git (required for cloning, can't be portable easily)
if command -v git &> /dev/null; then
    echo "[OK] Git: $(git --version | cut -d' ' -f3)"
else
    download_git
fi

# Download FFmpeg
download_ffmpeg
export PATH="$TOOLS_DIR/ffmpeg:$PATH"
echo "[OK] FFmpeg: downloaded"

# Download Python
download_python
# Ensure PYTHON_BIN is set (function might have returned early)
PYTHON_BIN="$TOOLS_DIR/python/bin/python3"
echo "[OK] Python: $($PYTHON_BIN --version 2>&1 | cut -d' ' -f2)"

# Check Node.js (optional)
if command -v npm &> /dev/null; then
    echo "[OK] Node.js: $(node --version 2>/dev/null || echo 'installed')"
else
    echo "[!] Node.js: not found (optional, for web UI)"
fi

echo ""
echo "All tools ready!"

# =============================================================================
# Clone/Update Repository
# =============================================================================
REPO_URL="https://github.com/hainguyen-keyti/stt.git"

echo ""
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating repository..."
    git pull
else
    echo "Cloning repository..."
    # Clone to temp and move contents
    TEMP_DIR=$(mktemp -d)
    git clone "$REPO_URL" "$TEMP_DIR"
    cp -r "$TEMP_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    cp -r "$TEMP_DIR"/.[!.]* "$INSTALL_DIR/" 2>/dev/null || true
    rm -rf "$TEMP_DIR"
fi

# =============================================================================
# Create virtual environment
# =============================================================================
# Check if venv exists but was created with wrong Python version
if [ -d "venv" ]; then
    VENV_PYTHON_VERSION=$(venv/bin/python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    EXPECTED_VERSION="3.11"
    if [ "$VENV_PYTHON_VERSION" != "$EXPECTED_VERSION" ]; then
        echo ""
        echo "Existing venv uses Python $VENV_PYTHON_VERSION, need $EXPECTED_VERSION"
        echo "Recreating virtual environment..."
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate

# Add FFmpeg to PATH in activate script
if ! grep -q "TOOLS_DIR" venv/bin/activate; then
    echo "" >> venv/bin/activate
    echo "# Added by 7KT-AI installer" >> venv/bin/activate
    echo "export PATH=\"$TOOLS_DIR/ffmpeg:\$PATH\"" >> venv/bin/activate
fi

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
# Setup .env
# =============================================================================
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
        echo "WARNING: Please edit .env to add your configuration"
    fi
fi

# =============================================================================
# Create start script that uses local tools
# =============================================================================
cat > "$INSTALL_DIR/start.sh" << 'STARTSCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

echo "=========================================="
echo "7KT-AI Server"
echo "=========================================="
echo "Web UI:   http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "=========================================="

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
STARTSCRIPT
chmod +x "$INSTALL_DIR/start.sh"

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  ./start.sh"
echo ""
echo "Web UI:   http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To uninstall, delete this directory"
echo ""
