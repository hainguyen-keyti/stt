@echo off
REM =============================================================================
REM 7KT-AI Native Installation Script (Windows)
REM Downloads Python locally - no system installation required
REM =============================================================================

setlocal enabledelayedexpansion

echo ==========================================
echo 7KT-AI Native Installation
echo ==========================================
echo.

REM Save original directory
set ORIGINAL_DIR=%CD%
set INSTALL_DIR=%USERPROFILE%\stt
set PYTHON_VERSION=3.11.9

REM =============================================================================
REM Check basic prerequisites (Git, FFmpeg)
REM =============================================================================
echo Checking prerequisites...
echo.

set MISSING=

REM Check Git
git --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] Git: not found
    set MISSING=!MISSING! Git
) else (
    for /f "tokens=3 delims= " %%v in ('git --version 2^>^&1') do echo [OK] Git: %%v
)

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] FFmpeg: not found
    set MISSING=!MISSING! FFmpeg
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
if not "!MISSING!"=="" (
    echo.
    echo ==========================================
    echo Missing prerequisites:!MISSING!
    echo ==========================================
    echo.
    echo Please install:
    echo.
    echo   Git:     https://git-scm.com/download/win
    echo.
    echo   FFmpeg:  https://github.com/BtbN/FFmpeg-Builds/releases
    echo            Download ffmpeg-master-latest-win64-gpl.zip
    echo            Extract to C:\ffmpeg and add C:\ffmpeg\bin to PATH
    echo.
    echo Or install with winget:
    echo   winget install Git.Git
    echo   winget install Gyan.FFmpeg
    echo.
    echo After installing, run this script again.
    pause
    exit /b 1
)

echo.
echo All prerequisites OK!
echo.

REM =============================================================================
REM Clone Repository
REM =============================================================================
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
REM Download standalone Python (no system install required)
REM =============================================================================
set PYTHON_DIR=%INSTALL_DIR%\.python
set PYTHON_BIN=%PYTHON_DIR%\python.exe

if exist "%PYTHON_BIN%" (
    echo.
    echo Using existing Python installation...
) else (
    echo.
    echo Downloading Python %PYTHON_VERSION% ^(standalone, local only^)...

    set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
    set PYTHON_ZIP=%TEMP%\python-embed.zip

    REM Download Python embeddable
    echo Downloading from: !PYTHON_URL!
    powershell -Command "Invoke-WebRequest -Uri '!PYTHON_URL!' -OutFile '!PYTHON_ZIP!'"

    REM Extract
    mkdir "%PYTHON_DIR%" 2>nul
    powershell -Command "Expand-Archive -Path '!PYTHON_ZIP!' -DestinationPath '%PYTHON_DIR%' -Force"
    del "!PYTHON_ZIP!"

    REM Enable pip for embeddable Python
    echo Configuring Python...

    REM Uncomment import site in python311._pth
    powershell -Command "(Get-Content '%PYTHON_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python311._pth'"

    REM Download get-pip.py
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"

    REM Install pip
    "%PYTHON_BIN%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location

    echo Python installed to: %PYTHON_DIR%
)

echo Python:
"%PYTHON_BIN%" --version

REM =============================================================================
REM Create virtual environment with local Python
REM =============================================================================
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    "%PYTHON_BIN%" -m venv venv
)

call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM =============================================================================
REM Detect NVIDIA GPU and install PyTorch
REM =============================================================================
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

REM =============================================================================
REM Install dependencies
REM =============================================================================
echo.
echo Installing dependencies...
pip install -r requirements.txt

echo Installing ASR engines...
pip install faster-whisper openai-whisper

echo Installing TTS engines...
pip install edge-tts gTTS pydub

echo Installing audio separator...
if %HAS_GPU% EQU 1 (
    pip install "audio-separator[gpu]" soundfile
) else (
    pip install "audio-separator[cpu]" soundfile
)

REM =============================================================================
REM Build frontend (optional)
REM =============================================================================
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

REM =============================================================================
REM Copy .env
REM =============================================================================
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
echo To uninstall completely, just delete:
echo   rmdir /s /q %INSTALL_DIR%
echo.

pause
