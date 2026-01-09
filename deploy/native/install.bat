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

REM Install directory = current directory where user runs the script
set "INSTALL_DIR=%CD%"
set "TOOLS_DIR=%INSTALL_DIR%\.tools"

echo Install directory: %INSTALL_DIR%

REM Create tools directory
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

REM =============================================================================
REM Download Git (portable)
REM =============================================================================
set "GIT_DIR=%TOOLS_DIR%\git"
set "GIT_BIN=%GIT_DIR%\cmd\git.exe"

if exist "%GIT_BIN%" (
    echo [OK] Git: already downloaded
) else (
    echo Downloading portable Git...
    set "GIT_VERSION=2.43.0"
    set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/PortableGit-2.43.0-64-bit.7z.exe"

    if not exist "%GIT_DIR%" mkdir "%GIT_DIR%"
    powershell -Command "Invoke-WebRequest -Uri '!GIT_URL!' -OutFile '%TOOLS_DIR%\git-portable.exe'"

    echo Extracting Git...
    "%TOOLS_DIR%\git-portable.exe" -o"%GIT_DIR%" -y
    del "%TOOLS_DIR%\git-portable.exe"
    echo Git installed to: %GIT_DIR%
)
set "PATH=%GIT_DIR%\cmd;%PATH%"

REM =============================================================================
REM Clone/Update Repository
REM =============================================================================
REM Check if this is a valid git repo by testing git status
"%GIT_BIN%" -C "%INSTALL_DIR%" rev-parse --git-dir >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Updating repository...
    "%GIT_BIN%" -C "%INSTALL_DIR%" pull
) else (
    echo Cloning repository...
    REM Remove any invalid .git folder
    if exist "%INSTALL_DIR%\.git" rmdir /s /q "%INSTALL_DIR%\.git"

    set "TEMP_CLONE=%TEMP%\stt-clone-%RANDOM%"
    "%GIT_BIN%" clone https://github.com/hainguyen-keyti/stt.git "!TEMP_CLONE!"
    if errorlevel 1 (
        echo ERROR: Failed to clone repository
        pause
        exit /b 1
    )
    xcopy /E /Y /H /Q "!TEMP_CLONE!\*" "%INSTALL_DIR%\" >nul
    rmdir /s /q "!TEMP_CLONE!"
    echo Repository cloned successfully.
)

REM =============================================================================
REM Download FFmpeg (portable)
REM =============================================================================
set "FFMPEG_DIR=%TOOLS_DIR%\ffmpeg"

if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    echo [OK] FFmpeg: already downloaded
) else (
    echo Downloading portable FFmpeg...
    if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile '%TOOLS_DIR%\ffmpeg.zip'"

    echo Extracting FFmpeg...
    powershell -Command "Expand-Archive -Path '%TOOLS_DIR%\ffmpeg.zip' -DestinationPath '%TOOLS_DIR%' -Force"

    for /d %%i in ("%TOOLS_DIR%\ffmpeg-*") do (
        xcopy /E /Y /Q "%%i\bin\*" "%FFMPEG_DIR%\" >nul
        rmdir /s /q "%%i"
    )
    del "%TOOLS_DIR%\ffmpeg.zip"
    echo FFmpeg installed to: %FFMPEG_DIR%
)
set "PATH=%FFMPEG_DIR%;%PATH%"

REM =============================================================================
REM Download Python (from NuGet - includes pip and venv)
REM =============================================================================
set "PYTHON_VERSION=3.11.9"
set "PYTHON_DIR=%TOOLS_DIR%\python"
set "PYTHON_BIN=%PYTHON_DIR%\python.exe"

if exist "%PYTHON_BIN%" (
    echo [OK] Python: already downloaded
) else (
    echo Downloading Python %PYTHON_VERSION%...
    if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"
    powershell -Command "Invoke-WebRequest -Uri 'https://www.nuget.org/api/v2/package/python/%PYTHON_VERSION%' -OutFile '%TOOLS_DIR%\python.zip'"

    echo Extracting Python...
    powershell -Command "Expand-Archive -Path '%TOOLS_DIR%\python.zip' -DestinationPath '%TOOLS_DIR%\python-temp' -Force"

    xcopy /E /Y /Q "%TOOLS_DIR%\python-temp\tools\*" "%PYTHON_DIR%\" >nul
    rmdir /s /q "%TOOLS_DIR%\python-temp"
    del "%TOOLS_DIR%\python.zip"
    echo Python installed to: %PYTHON_DIR%
)
set "PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%"

REM =============================================================================
REM Download Node.js (portable)
REM =============================================================================
set "NODE_VERSION=20.18.1"
set "NODE_DIR=%TOOLS_DIR%\node"
set "NODE_BIN=%NODE_DIR%\node.exe"
set "NPM_BIN=%NODE_DIR%\npm.cmd"

if exist "%NODE_BIN%" (
    echo [OK] Node.js: already downloaded
) else (
    echo Downloading Node.js %NODE_VERSION%...
    if not exist "%NODE_DIR%" mkdir "%NODE_DIR%"
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v%NODE_VERSION%/node-v%NODE_VERSION%-win-x64.zip' -OutFile '%TOOLS_DIR%\node.zip'"

    echo Extracting Node.js...
    powershell -Command "Expand-Archive -Path '%TOOLS_DIR%\node.zip' -DestinationPath '%TOOLS_DIR%' -Force"

    for /d %%i in ("%TOOLS_DIR%\node-v*") do (
        xcopy /E /Y /Q "%%i\*" "%NODE_DIR%\" >nul
        rmdir /s /q "%%i"
    )
    del "%TOOLS_DIR%\node.zip"
    echo Node.js installed to: %NODE_DIR%
)
set "PATH=%NODE_DIR%;%PATH%"

REM Show status
echo.
echo ==========================================
echo All tools downloaded:
echo   Git:    %GIT_DIR%
echo   FFmpeg: %FFMPEG_DIR%
echo   Python: %PYTHON_DIR%
echo   Node:   %NODE_DIR%
echo ==========================================
echo.

REM =============================================================================
REM Create virtual environment
REM =============================================================================
if not exist "%INSTALL_DIR%\venv" (
    echo Creating virtual environment...
    "%PYTHON_BIN%" -m venv "%INSTALL_DIR%\venv"
)

call "%INSTALL_DIR%\venv\Scripts\activate.bat"

REM Upgrade pip
"%PYTHON_BIN%" -m pip install --upgrade pip

REM =============================================================================
REM Detect NVIDIA GPU and install PyTorch
REM =============================================================================
echo.
echo Detecting hardware...
set "HAS_GPU=0"
nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo NVIDIA GPU detected - Installing PyTorch with CUDA
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    set "HAS_GPU=1"
) else (
    echo No NVIDIA GPU detected - Installing PyTorch CPU
    pip install torch torchvision torchaudio
)

REM =============================================================================
REM Install dependencies
REM =============================================================================
echo.
echo Installing dependencies...
pip install -r "%INSTALL_DIR%\requirements.txt"

echo Installing ASR engines...
pip install faster-whisper openai-whisper

echo Installing TTS engines...
pip install edge-tts gTTS pydub

echo Installing audio separator...
if "!HAS_GPU!"=="1" (
    pip install "audio-separator[gpu]" soundfile
) else (
    pip install "audio-separator[cpu]" soundfile
)

REM =============================================================================
REM Build frontend
REM =============================================================================
echo.
echo Building frontend...
pushd "%INSTALL_DIR%\web"
if errorlevel 1 (
    echo ERROR: web directory not found at %INSTALL_DIR%\web
    pause
    exit /b 1
)
call "%NPM_BIN%" install
call "%NPM_BIN%" run build
popd

REM =============================================================================
REM Setup .env
REM =============================================================================
if not exist "%INSTALL_DIR%\.env" (
    if exist "%INSTALL_DIR%\.env.example" (
        copy "%INSTALL_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul
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
echo set "PATH=%%~dp0.tools\node;%%~dp0.tools\ffmpeg;%%~dp0.tools\git\cmd;%%~dp0.tools\python;%%~dp0.tools\python\Scripts;%%PATH%%"
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
