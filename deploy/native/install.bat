@echo off
REM =============================================================================
REM 7KT-AI Native Installation Script (Windows)
REM Auto-detects hardware and installs optimal dependencies
REM =============================================================================

echo ==========================================
echo 7KT-AI Native Installation
echo ==========================================
echo.

REM =============================================================================
REM Check Prerequisites
REM =============================================================================
echo Checking prerequisites...
echo.

set MISSING=

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] Python: not found
    set MISSING=%MISSING% Python
) else (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do echo [OK] Python: %%v
)

REM Check Git
git --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] Git: not found
    set MISSING=%MISSING% Git
) else (
    for /f "tokens=3 delims= " %%v in ('git --version 2^>^&1') do echo [OK] Git: %%v
)

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] FFmpeg: not found
    set MISSING=%MISSING% FFmpeg
) else (
    echo [OK] FFmpeg: installed
)

REM Check Node.js (optional)
npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Node.js: not found ^(optional, for web UI^)
) else (
    for /f %%v in ('node --version 2^>^&1') do echo [OK] Node.js: %%v
)

REM If missing prerequisites, show install instructions
if not "%MISSING%"=="" (
    echo.
    echo ==========================================
    echo Missing prerequisites:%MISSING%
    echo ==========================================
    echo.
    echo Please install the following:
    echo.
    echo   Python 3.10+:  https://www.python.org/downloads/
    echo                  [!] Check "Add Python to PATH" when installing
    echo.
    echo   Git:           https://git-scm.com/download/win
    echo.
    echo   FFmpeg:        https://github.com/BtbN/FFmpeg-Builds/releases
    echo                  Download ffmpeg-master-latest-win64-gpl.zip
    echo                  Extract to C:\ffmpeg and add C:\ffmpeg\bin to PATH
    echo.
    echo   Node.js:       https://nodejs.org/ ^(optional^)
    echo.
    echo Or install with winget:
    echo   winget install Python.Python.3.11
    echo   winget install Git.Git
    echo   winget install Gyan.FFmpeg
    echo   winget install OpenJS.NodeJS
    echo.
    echo After installing, run this script again.
    pause
    exit /b 1
)

echo.
echo All prerequisites OK!
echo.

REM Save original directory (where user runs script from)
set ORIGINAL_DIR=%CD%

REM =============================================================================
REM Clone Repository
REM =============================================================================
set INSTALL_DIR=%USERPROFILE%\stt

if exist "%INSTALL_DIR%" (
    echo Updating existing installation...
    cd /d "%INSTALL_DIR%"
    git pull
) else (
    echo Cloning repository...
    git clone https://github.com/hainguyen-keyti/stt.git "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)

REM =============================================================================
REM Installation
REM =============================================================================

REM Create virtual environment
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
)

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
npm --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Building frontend...
    cd web
    npm install
    npm run build
    cd ..
) else (
    echo Skipping frontend build ^(Node.js not installed^)
)

REM Copy .env from original directory if provided, otherwise use .env.example
if exist "%ORIGINAL_DIR%\.env" (
    copy "%ORIGINAL_DIR%\.env" .env
    echo Copied .env from %ORIGINAL_DIR%
) else (
    if not exist ".env" (
        if exist ".env.example" (
            copy .env.example .env
            echo Created .env from .env.example
            echo WARNING: Please edit .env to add your configuration
        )
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
echo Web UI:   http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.

pause
