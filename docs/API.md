# Professional Subtitle Generation Service - API Documentation

**Version:** 4.0.0
**Base URL:** `http://localhost:8000`
**Interactive Docs:** `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Endpoints](#endpoints)
   - [Subtitle Generation](#subtitle-generation)
   - [Presets](#presets)
   - [Metrics](#metrics)
   - [Health](#health)
4. [ASR Engines](#asr-engines)
5. [Models](#models)
6. [Error Handling](#error-handling)

---

## Overview

This API provides professional-quality subtitle generation from audio/video files with:

- **Multiple ASR Engines:** faster-whisper (speed) and OpenAI Whisper (accuracy)
- **Output Formats:** SRT (subtitle file) and JSON (full transcription data)
- **Advanced Options:** VAD filtering, word-level timestamps, beam search tuning
- **Preset Configurations:** Pre-configured settings for different use cases

---

## Quick Start

### Generate SRT Subtitles

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -F "audio_file=@video.mp3" \
  -F "format=srt" \
  --output subtitle.srt
```

### Generate JSON Transcription

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -F "audio_file=@video.mp3" \
  -F "format=json"
```

### With Custom Settings

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -F "audio_file=@video.mp3" \
  -F "format=srt" \
  -F "engine=openai-whisper" \
  -F "model_size=turbo" \
  -F "language=zh" \
  -F "beam_size=10" \
  --output subtitle.srt
```

---

## Endpoints

### Subtitle Generation

**POST** `/subtitle`

Generate subtitle file (SRT) or transcription data (JSON) from audio.

#### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `audio_file` | File | *required* | Audio file (MP3, WAV, M4A, FLAC, OGG, OPUS, WebM) |
| `format` | string | `srt` | Output format (`srt`, `json`) |
| `engine` | string | `faster-whisper` | ASR engine (`faster-whisper`, `openai-whisper`) |
| `model_size` | string | `large-v3` | Model size (see [Models](#models)) |
| `compute_type` | string | auto | Quantization (`int8`, `float16`, `float32`) |
| `language` | string | auto | ISO 639-1 code (e.g., `en`, `zh`, `vi`) |
| `vad_filter` | bool | `true` | Enable voice activity detection |
| `word_timestamps` | bool | `true` | Include word-level timestamps |
| `batch_size` | int | `16` | Batch size (1-64) |
| `beam_size` | int | `5` | Beam search size (1-20) |
| `temperature` | float | `0.0` | Sampling temperature (0.0-1.0) |
| `best_of` | int | `5` | Best of N samples (OpenAI Whisper) |
| `condition_on_previous_text` | bool | `true` | Use previous segment as context |
| `no_speech_threshold` | float | `0.6` | No speech detection threshold |
| `compression_ratio_threshold` | float | `2.4` | Reject hallucinations threshold |
| `logprob_threshold` | float | `-1.0` | Reject low confidence threshold |
| `initial_prompt` | string | null | Initial prompt for context |

**SRT-only parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `word_level` | bool | `false` | One word per subtitle line |
| `max_line_width` | int | `42` | Max characters per line (10-100) |
| `max_line_count` | int | `2` | Max lines per subtitle (1-3) |
| `adjust_timing` | bool | `false` | Adjust timing for natural reading |

#### Response (format=srt)

Returns SRT file content with headers:

- `Content-Type`: `text/srt; charset=utf-8`
- `Content-Disposition`: `attachment; filename="audio.srt"`
- `X-Processing-Time-Ms`: Total processing time
- `X-Inference-Time-Ms`: Inference time only

```
1
00:00:00,000 --> 00:00:02,500
Hello world.

2
00:00:02,800 --> 00:00:05,200
This is a test.
```

#### Response (format=json)

Returns full transcription data:

```json
{
  "text": "Full transcription text...",
  "language": "en",
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Hello world.",
      "words": [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world.", "start": 0.6, "end": 1.0}
      ]
    }
  ],
  "words": [...],
  "metadata": {
    "engine": "faster-whisper",
    "model_size": "large-v3",
    "language": "en",
    "preprocessing": "vad_only",
    "audio_duration_s": 120.5,
    "inference_time_ms": 15234.5,
    "preprocessing_time_ms": 1200.0,
    "total_time_ms": 16434.5,
    "real_time_factor": 0.14,
    "vram_used_mb": 4500.0
  }
}
```

---

### Presets

**GET** `/presets/`

List all available preset configurations with full details.

#### Response

```json
[
  {
    "id": "dialogue",
    "title": "Dialogue",
    "engine": "openai-whisper",
    "description": "Optimal settings for dialogue transcription",
    "transcription": {
      "model_size": "turbo",
      "language": "zh",
      "word_timestamps": true,
      "beam_size": 10,
      "temperature": 0.0,
      "best_of": 5,
      "condition_on_previous_text": false,
      "no_speech_threshold": 0.5,
      "compression_ratio_threshold": 2.0,
      "logprob_threshold": -0.8
    },
    "formatter": {
      "max_line_width": 18,
      "max_line_count": 1,
      "adjust_timing": false
    }
  },
  {
    "id": "fast",
    "title": "Fast",
    "engine": "faster-whisper",
    "description": "Fastest processing with good accuracy",
    "transcription": {...},
    "formatter": {...}
  }
]
```

---

### Metrics

**GET** `/metrics`

Get service performance metrics.

```json
{
  "requests_total": 1523,
  "requests_last_hour": 45,
  "requests_per_minute": 0.75,
  "avg_inference_time_ms": 2156.3,
  "p50_inference_time_ms": 1800.0,
  "p95_inference_time_ms": 4200.0,
  "p99_inference_time_ms": 8500.0,
  "gpu_utilization_percent": 72.5,
  "vram_usage_percent": 45.2,
  "cache_hit_rate": 0.67,
  "error_rate": 0.02
}
```

---

### Health

**GET** `/health`

Check service health status.

```json
{
  "status": "healthy",
  "uptime_seconds": 3600.0,
  "version": "4.0.0"
}
```

**GET** `/`

Root endpoint with service info.

```json
{
  "service": "Professional Subtitle Generation Service",
  "version": "4.0.0",
  "status": "operational",
  "documentation": "/docs",
  "api_docs": "/redoc"
}
```

---

## ASR Engines

### faster-whisper

- **Speed:** 4x faster than OpenAI Whisper
- **Best for:** Batch processing, long videos
- **Models:** tiny, base, small, medium, large-v2, large-v3, distil-large-v3

### openai-whisper

- **Accuracy:** Official implementation with natural segmentation
- **Best for:** High-quality dialogue, movies
- **Models:** tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large, large-v2, large-v3, turbo

---

## Models

### faster-whisper Models

| Model | VRAM | Speed | Use Case |
|-------|------|-------|----------|
| tiny | ~1GB | Fastest | Testing |
| base | ~1GB | Very Fast | Quick drafts |
| small | ~2GB | Fast | Balance |
| medium | ~5GB | Moderate | Good quality |
| large-v2 | ~10GB | Slow | High quality |
| large-v3 | ~10GB | Slow | Best quality |
| distil-large-v3 | ~6GB | Fast | Quality + Speed |

### openai-whisper Models

| Model | VRAM | Speed | Use Case |
|-------|------|-------|----------|
| tiny/tiny.en | ~1GB | Fastest | Testing |
| base/base.en | ~1GB | Very Fast | Quick drafts |
| small/small.en | ~2GB | Fast | Balance |
| medium/medium.en | ~5GB | Moderate | Good quality |
| large/large-v2/large-v3 | ~10GB | Slow | Best quality |
| turbo | ~6GB | Fast | **Recommended** |

> `.en` models are English-only and slightly more accurate for English.

---

## Error Handling

### Error Response Format

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "remediation": "How to fix",
  "details": {}
}
```

### HTTP Status Codes

| Code | Error | Description |
|------|-------|-------------|
| 400 | Bad Request | Invalid request format |
| 413 | file_too_large | File exceeds 500MB limit |
| 415 | unsupported_media_type | Invalid audio format |
| 422 | validation_error | Invalid parameters |
| 500 | audio_processing_error | Transcription failed |
| 503 | model_load_error | Model loading failed |
| 507 | insufficient_vram | Not enough GPU memory |

---

## Advanced Usage

### Optimal Settings for Movie Subtitles

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -F "audio_file=@movie.mp3" \
  -F "engine=openai-whisper" \
  -F "model_size=turbo" \
  -F "beam_size=10" \
  -F "temperature=0.0" \
  -F "vad_filter=true" \
  -F "format=srt" \
  -F "max_line_width=42" \
  -F "max_line_count=2" \
  --output movie.srt
```

### Using initial_prompt for Context

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -F "audio_file=@lecture.mp3" \
  -F "engine=openai-whisper" \
  -F "initial_prompt=This is a lecture about machine learning and neural networks." \
  --output lecture.srt
```

---

## Rate Limits

- **Max file size:** 500MB
- **Request timeout:** 5 minutes (300 seconds)
- **Concurrent requests:** Limited by GPU memory

---

## Running the Server

```bash
# Development
cd /path/to/stt
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> **Note:** Use `--workers 1` for GPU inference to avoid memory conflicts.
