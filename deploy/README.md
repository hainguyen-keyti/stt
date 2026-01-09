# 7KT-AI Deployment

## Quick Start

### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

### Windows
```batch
start.bat
```

### Docker Compose
```bash
# CPU
docker-compose up -d

# GPU (NVIDIA)
docker-compose --profile gpu up -d
```

## Access

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Commands

```bash
# View logs
docker logs -f 7kt-ai

# Stop
docker-compose down

# Restart
docker-compose restart

# Update to latest
docker-compose pull && docker-compose up -d
```

## Configuration

Edit `.env` file to configure database, API keys, etc.
