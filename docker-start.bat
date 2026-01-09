@echo off
REM =============================================================================
REM Auto-detect hardware and start STT service with optimal configuration
REM Usage: docker-start.bat [build|up|down|logs]
REM =============================================================================

setlocal enabledelayedexpansion

REM Default command
if "%1"=="" (
    set CMD=start
) else (
    set CMD=%1
)

REM Detect NVIDIA GPU
set GPU_DETECTED=0
set TARGET_PLATFORM=cpu

where nvidia-smi >nul 2>&1
if %errorlevel%==0 (
    nvidia-smi >nul 2>&1
    if %errorlevel%==0 (
        set GPU_DETECTED=1
        set TARGET_PLATFORM=gpu
        for /f "tokens=*" %%i in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do set GPU_NAME=%%i
        echo [INFO] NVIDIA GPU detected: !GPU_NAME!
    )
)

if %GPU_DETECTED%==0 (
    echo [INFO] No NVIDIA GPU detected, using CPU mode
)

echo [INFO] Target platform: %TARGET_PLATFORM%

REM Execute command
if "%CMD%"=="build" goto build
if "%CMD%"=="up" goto up
if "%CMD%"=="down" goto down
if "%CMD%"=="stop" goto down
if "%CMD%"=="logs" goto logs
if "%CMD%"=="start" goto start
if "%CMD%"=="restart" goto restart
if "%CMD%"=="status" goto status
goto usage

:build
echo [INFO] Building Docker image for %TARGET_PLATFORM%...
if "%TARGET_PLATFORM%"=="gpu" (
    docker-compose build --build-arg TARGET_PLATFORM=gpu
) else (
    docker-compose build --build-arg TARGET_PLATFORM=cpu
)
echo [INFO] Build completed
goto end

:up
echo [INFO] Starting STT service...
if "%TARGET_PLATFORM%"=="gpu" (
    docker-compose --profile gpu up -d
) else (
    docker-compose up -d
)
echo [INFO] Service started
echo [INFO] Access the service at: http://localhost:8000
echo [INFO] API Documentation: http://localhost:8000/docs
echo [INFO] Hardware Info: http://localhost:8000/hardware
goto end

:down
echo [INFO] Stopping STT service...
docker-compose --profile gpu down 2>nul || docker-compose down
echo [INFO] Service stopped
goto end

:logs
if "%TARGET_PLATFORM%"=="gpu" (
    docker-compose logs -f stt-gpu
) else (
    docker-compose logs -f stt
)
goto end

:start
call :build
call :up
goto end

:restart
call :down
call :start
goto end

:status
echo [INFO] Service status:
docker-compose ps
goto end

:usage
echo Usage: docker-start.bat {start^|build^|up^|down^|logs^|restart^|status}
echo.
echo Commands:
echo   start   - Build and start service (default)
echo   build   - Build Docker image only
echo   up      - Start service (assumes already built)
echo   down    - Stop service
echo   logs    - Show service logs
echo   restart - Restart service
echo   status  - Show service status
goto end

:end
endlocal
