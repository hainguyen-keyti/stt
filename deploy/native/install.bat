@echo off
REM =============================================================================
REM 7KT-AI Native Installation Script (Windows)
REM Auto-detects hardware and installs optimal dependencies
REM =============================================================================

echo ==========================================
echo 7KT-AI Native Installation
echo ==========================================

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is required but not installed
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo Python: %PYTHON_VERSION%

REM Set install directory
set INSTALL_DIR=%USERPROFILE%\stt

REM Clone or update repository
if exist "%INSTALL_DIR%" (
    echo Updating existing installation...
    cd /d "%INSTALL_DIR%"
    git pull
) else (
    echo Cloning repository...
    git clone https://github.com/hainguyen-keyti/stt.git "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Detect NVIDIA GPU
echo.
echo Detecting hardware...
nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo NVIDIA GPU detected - Installing PyTorch with CUDA
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    set HAS_GPU=1
) else (
    echo No NVIDIA GPU detected - Installing PyTorch CPU
    pip install torch torchvision torchaudio
    set HAS_GPU=0
)

REM Install requirements
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Install ASR engines
echo Installing ASR engines...
pip install faster-whisper openai-whisper

REM Install TTS engines
echo Installing TTS engines...
pip install edge-tts gTTS pydub

REM Install audio separator
echo Installing audio separator...
if %HAS_GPU% EQU 1 (
    pip install "audio-separator[gpu]" soundfile
) else (
    pip install "audio-separator[cpu]" soundfile
)

REM Build frontend
echo.
echo Building frontend...
where npm >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    cd web
    npm install
    npm run build
    cd ..
) else (
    echo WARNING: npm not found, skipping frontend build
    echo Install Node.js from https://nodejs.org/ if you need the web UI
)

REM Create .env if not exists
if not exist .env (
    echo Creating .env file...
    if exist .env.example (
        copy .env.example .env
    ) else (
        echo # Add your configuration here > .env
    )
)

echo.
echo ==========================================
echo Installation complete!
echo ==========================================
echo.
echo To start the server:
echo   cd %INSTALL_DIR%
echo   start.bat
echo.
echo Or manually:
echo   venv\Scripts\activate.bat
echo   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
echo.

pause
