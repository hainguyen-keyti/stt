#!/bin/bash
# =============================================================================
# Auto-detect hardware and start STT service with optimal configuration
# Usage: ./docker-start.sh [build|up|down|logs]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect NVIDIA GPU
detect_nvidia_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            echo "nvidia"
            return 0
        fi
    fi
    echo "none"
    return 1
}

# Detect hardware and set variables
detect_hardware() {
    echo -e "${BLUE}Detecting hardware...${NC}"

    GPU_TYPE=$(detect_nvidia_gpu)

    if [ "$GPU_TYPE" = "nvidia" ]; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)
        GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -n1)
        echo -e "${GREEN}✓ NVIDIA GPU detected: ${GPU_NAME} (${GPU_MEMORY})${NC}"
        TARGET_PLATFORM="gpu"
        COMPOSE_PROFILES="gpu"
        SERVICE_NAME="stt-gpu"
    else
        echo -e "${YELLOW}No NVIDIA GPU detected, using CPU mode${NC}"
        TARGET_PLATFORM="cpu"
        COMPOSE_PROFILES=""
        SERVICE_NAME="stt"
    fi

    echo -e "${BLUE}Target platform: ${TARGET_PLATFORM}${NC}"
}

# Build Docker image
build() {
    detect_hardware

    echo -e "${BLUE}Building Docker image for ${TARGET_PLATFORM}...${NC}"

    if [ "$TARGET_PLATFORM" = "gpu" ]; then
        docker-compose build --build-arg TARGET_PLATFORM=gpu
    else
        docker-compose build --build-arg TARGET_PLATFORM=cpu
    fi

    echo -e "${GREEN}✓ Build completed${NC}"
}

# Start service
up() {
    detect_hardware

    echo -e "${BLUE}Starting STT service...${NC}"

    if [ "$TARGET_PLATFORM" = "gpu" ]; then
        docker-compose --profile gpu up -d
    else
        docker-compose up -d
    fi

    echo -e "${GREEN}✓ Service started${NC}"
    echo -e "${BLUE}Access the service at: http://localhost:8000${NC}"
    echo -e "${BLUE}API Documentation: http://localhost:8000/docs${NC}"
    echo -e "${BLUE}Hardware Info: http://localhost:8000/hardware${NC}"
}

# Stop service
down() {
    echo -e "${BLUE}Stopping STT service...${NC}"
    docker-compose --profile gpu down 2>/dev/null || docker-compose down
    echo -e "${GREEN}✓ Service stopped${NC}"
}

# Show logs
logs() {
    detect_hardware
    docker-compose logs -f $SERVICE_NAME
}

# Build and start
start() {
    build
    up
}

# Show status
status() {
    echo -e "${BLUE}Service status:${NC}"
    docker-compose ps
}

# Main
case "${1:-start}" in
    build)
        build
        ;;
    up)
        up
        ;;
    down|stop)
        down
        ;;
    logs)
        logs
        ;;
    start)
        start
        ;;
    restart)
        down
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|build|up|down|logs|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Build and start service (default)"
        echo "  build   - Build Docker image only"
        echo "  up      - Start service (assumes already built)"
        echo "  down    - Stop service"
        echo "  logs    - Show service logs"
        echo "  restart - Restart service"
        echo "  status  - Show service status"
        exit 1
        ;;
esac
