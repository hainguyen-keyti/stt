@echo off
REM =============================================================================
REM 7KT-AI Start Script (Windows)
REM =============================================================================

cd /d "%~dp0"

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

echo ==========================================
echo Starting 7KT-AI Server
echo ==========================================
echo.
echo Web UI:    http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop
echo.

REM Start server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
