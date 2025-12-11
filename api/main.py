"""
Professional Subtitle Generation Service v4.0 - FastAPI Application

Main application entry point with core configuration and routing.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import time

from api.utils.errors import register_exception_handlers
from api.utils.logging import setup_logging
from api.routers import subtitle, metrics, presets

# Setup logging
setup_logging(log_level="INFO", use_json=False)  # Use simple format for development

# Track service start time for uptime calculation
START_TIME = time.time()

# Create FastAPI application
app = FastAPI(
    title="Professional Subtitle Generation Service",
    version="4.0.0",
    description=(
        "Production-ready backend API for generating professional-quality subtitles "
        "from audio and video files. Supports multiple ASR engines (faster-whisper, "
        "openai-whisper) with SRT and JSON export."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register routers
app.include_router(subtitle.router, tags=["Subtitles"])
app.include_router(metrics.router, tags=["Monitoring"])
app.include_router(presets.router, tags=["Presets"])


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing service information.

    Returns basic service metadata and status.
    """
    return {
        "service": "Professional Subtitle Generation Service",
        "version": "4.0.0",
        "status": "operational",
        "documentation": "/docs",
        "api_docs": "/redoc",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns service health status. Will be enhanced with GPU info
    and model status in later phases.
    """
    uptime_seconds = time.time() - START_TIME

    return {
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "version": "4.0.0",
    }


# Serve static frontend files in production
STATIC_DIR = Path(__file__).parent.parent / "web" / "dist"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve frontend SPA for all non-API routes."""
        # Skip API routes
        if full_path.startswith(("docs", "redoc", "openapi.json", "subtitle", "presets", "metrics", "health")):
            return None
        # Serve index.html for SPA routing
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not found"}
