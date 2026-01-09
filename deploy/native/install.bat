@echo off
REM =============================================================================
REM 7KT-AI Native Installation Script (Windows)
REM Downloads everything locally - no system installation required
REM =============================================================================

setlocal enabledelayedexpansion

echo ==========================================
echo 7KT-AI Native Installation
echo ==========================================
echo.

REM Install directory = current directory
set INSTALL_DIR=%CD%
set TOOLS_DIR=%INSTALL_DIR%\.tools

REM Create tools directory
mkdir "%TOOLS_DIR%" 2>nul

REM =============================================================================
REM Download Git (portable)
REM =============================================================================
:download_git
set GIT_DIR=%TOOLS_DIR%\git
set GIT_BIN=%GIT_DIR%\cmd\git.exe

if exist "%GIT_BIN%" (
    echo [OK] Git: already downloaded
    goto :git_done
)

echo Downloading portable Git...
set GIT_VERSION=2.43.0
set GIT_URL=https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-64-bit.7z.exe

mkdir "%GIT_DIR%" 2>nul
powershell -Command "Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%TOOLS_DIR%\git-portable.exe'"

REM Extract (self-extracting archive)
echo Extracting Git...
"%TOOLS_DIR%\git-portable.exe" -o"%GIT_DIR%" -y
del "%TOOLS_DIR%\git-portable.exe"

echo Git installed to: %GIT_DIR%

:git_done
set PATH=%GIT_DIR%\cmd;%PATH%

REM =============================================================================
REM Download FFmpeg (portable)
REM =============================================================================
:download_ffmpeg
set FFMPEG_DIR=%TOOLS_DIR%\ffmpeg

if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    echo [OK] FFmpeg: already downloaded
    goto :ffmpeg_done
)

echo Downloading portable FFmpeg...
set FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip

mkdir "%FFMPEG_DIR%" 2>nul
powershell -Command "Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%TOOLS_DIR%\ffmpeg.zip'"

REM Extract
echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Path '%TOOLS_DIR%\ffmpeg.zip' -DestinationPath '%TOOLS_DIR%' -Force"

REM Move files from subfolder
for /d %%i in ("%TOOLS_DIR%\ffmpeg-*") do (
    xcopy /E /Y "%%i\bin\*" "%FFMPEG_DIR%\" >nul
    rmdir /s /q "%%i"
)
del "%TOOLS_DIR%\ffmpeg.zip"

echo FFmpeg installed to: %FFMPEG_DIR%

:ffmpeg_done
set PATH=%FFMPEG_DIR%;%PATH%

REM =============================================================================
REM Download Python (standalone installer version, not embeddable)
REM =============================================================================
:download_python
set PYTHON_VERSION=3.11.9
set PYTHON_DIR=%TOOLS_DIR%\python
set PYTHON_BIN=%PYTHON_DIR%\python.exe
set PIP_BIN=%PYTHON_DIR%\Scripts\pip.exe

if exist "%PYTHON_BIN%" (
    echo [OK] Python: already downloaded
    goto :python_done
)

echo Downloading Python %PYTHON_VERSION%...
REM Use nuget package which includes full Python with pip and venv
set PYTHON_URL=https://www.nuget.org/api/v2/package/python/%PYTHON_VERSION%

mkdir "%PYTHON_DIR%" 2>nul
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TOOLS_DIR%\python.nupkg'"

REM Extract (nupkg is just a zip)
echo Extracting Python...
powershell -Command "Expand-Archive -Path '%TOOLS_DIR%\python.nupkg' -DestinationPath '%TOOLS_DIR%\python-temp' -Force"

REM Move from tools subfolder
xcopy /E /Y "%TOOLS_DIR%\python-temp\tools\*" "%PYTHON_DIR%\" >nul
rmdir /s /q "%TOOLS_DIR%\python-temp"
del "%TOOLS_DIR%\python.nupkg"

echo Python installed to: %PYTHON_DIR%

:python_done
set PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%

REM Show status
echo.
echo [OK] Git: downloaded
echo [OK] FFmpeg: downloaded
echo [OK] Python: downloaded

REM Check Node.js (optional)
npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Node.js: not found ^(optional, for web UI^)
) else (
    for /f %%v in ('node --version 2^>^&1') do echo [OK] Node.js: %%v
)

echo.
echo All tools ready!
echo.

REM =============================================================================
REM Clone/Update Repository
REM =============================================================================
if exist "%INSTALL_DIR%\.git" (
    echo Updating repository...
    "%GIT_BIN%" pull
) else (
    echo Cloning repository...
    REM Clone to temp and move contents
    set TEMP_CLONE=%TEMP%\stt-temp-%RANDOM%
    "%GIT_BIN%" clone https://github.com/hainguyen-keyti/stt.git "!TEMP_CLONE!"
    xcopy /E /Y "!TEMP_CLONE!\*" "%INSTALL_DIR%\" >nul
    rmdir /s /q "!TEMP_CLONE!"
)

REM =============================================================================
REM Create virtual environment
REM =============================================================================
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    "%PYTHON_BIN%" -m venv venv
)

call venv\Scripts\activate.bat

REM Upgrade pip
"%PYTHON_DIR%\python.exe" -m pip install --upgrade pip

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
REM Setup .env
REM =============================================================================
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo Created .env from .env.example
        echo WARNING: Please edit .env to add your configuration
    )
)

REM =============================================================================
REM Create start script
REM =============================================================================
(
echo @echo off
echo cd /d "%%~dp0"
echo set PATH=%%~dp0.tools\ffmpeg;%%~dp0.tools\git\cmd;%%~dp0.tools\python;%%~dp0.tools\python\Scripts;%%PATH%%
echo call venv\Scripts\activate.bat
echo echo ==========================================
echo echo 7KT-AI Server
echo echo ==========================================
echo echo Web UI:   http://localhost:8000
echo echo API Docs: http://localhost:8000/docs
echo echo ==========================================
echo python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
) > "%INSTALL_DIR%\start.bat"

echo.
echo ==========================================
echo Installation complete!
echo ==========================================
echo.
echo To start the server:
echo   start.bat
echo.
echo Web UI:   http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo To uninstall, delete this directory
echo.

pause
