#!/bin/bash
# =============================================================================
# 7KT-AI Start Script (Linux/Mac)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found"
    echo "Please run install.sh first"
    exit 1
fi

echo "=========================================="
echo "Starting 7KT-AI Server"
echo "=========================================="
echo ""
echo "Web UI:    http://localhost:8000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
