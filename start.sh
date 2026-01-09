#!/bin/bash
# 7KT-AI Start Script

cd "$(dirname "$0")"
source venv/bin/activate

echo "=========================================="
echo "7KT-AI Server"
echo "=========================================="
echo "Web UI:   http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "=========================================="

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
