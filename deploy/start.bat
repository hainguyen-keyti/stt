@echo off
REM =============================================================================
REM 7KT-AI Quick Start Script for Windows
REM Auto-detects hardware and runs with optimal configuration
REM =============================================================================

echo ==========================================
echo 7KT-AI Service Launcher
echo ==========================================

REM Check Docker
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker daemon is not running
    echo Please start Docker Desktop
    pause
    exit /b 1
)

REM Pull latest image
echo Pulling latest image...
docker pull keytikontum/7kt-ai:latest

REM Check for NVIDIA GPU
set GPU_ARGS=
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo NVIDIA GPU detected!
    set GPU_ARGS=--gpus all
    echo Running with GPU acceleration
) else (
    echo No NVIDIA GPU detected, running on CPU
)

REM Stop existing container
echo Stopping existing container (if any)...
docker stop 7kt-ai 2>nul
docker rm 7kt-ai 2>nul

REM Run container
echo Starting container...
docker run -d ^
    --name 7kt-ai ^
    -p 8000:8000 ^
    -v whisper-cache:/root/.cache/whisper ^
    -v hf-cache:/root/.cache/huggingface ^
    -v torch-cache:/root/.cache/torch ^
    --restart unless-stopped ^
    %GPU_ARGS% ^
    keytikontum/7kt-ai:latest

echo.
echo ==========================================
echo 7KT-AI is starting...
echo ==========================================
echo.
echo Web UI:    http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo.
echo View logs: docker logs -f 7kt-ai
echo Stop:      docker stop 7kt-ai
echo.

pause
