# Audio Processing Service - API Documentation

**Version:** 4.0.0
**Base URL:** `http://localhost:8000`
**Interactive Docs:** `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Text-to-Speech (TTS)](#text-to-speech-tts)
   - [Voices](#tts-voices)
   - [Synthesize](#tts-synthesize)
   - [Time Adjust Mode](#tts-time-adjust)
   - [Engines](#tts-engines)
4. [Audio Separator](#audio-separator)
   - [Submit Job](#separator-submit)
   - [Job Status](#separator-status)
   - [Models](#separator-models)
5. [Subtitle Generation (STT)](#subtitle-generation-stt)
   - [Generate Subtitle](#stt-generate)
   - [ASR Engines](#asr-engines)
   - [Models](#stt-models)
6. [Health & Metrics](#health--metrics)
7. [Error Handling](#error-handling)

---

## Overview

This API provides professional audio processing services:

- **Text-to-Speech (TTS):** Convert text to speech with multiple Vietnamese voices
- **Audio Separator:** Separate vocals and instrumental from audio files
- **Subtitle Generation (STT):** Generate subtitles from audio/video files

---

## Quick Start

### TTS - Convert Text to Speech

```bash
curl -X POST "http://localhost:8000/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào, tôi là trợ lý ảo.",
    "voice_id": "vi-VN-HoaiMyNeural",
    "pitch": 0,
    "speed": 1.0
  }'
```

### Audio Separator - Remove Vocals

```bash
curl -X POST "http://localhost:8000/separator/" \
  -F "audio_file=@song.mp3" \
  -F "vocal_volume=0.0" \
  -F "instrumental_volume=1.0" \
  -F "model=fast"
```

### STT - Generate Subtitles

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -F "audio_file=@video.mp3" \
  -F "format=srt" \
  --output subtitle.srt
```

---

## Text-to-Speech (TTS)

### TTS Voices

**GET** `/tts/voices`

List all available TTS voices.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `language` | string | null | Filter by language (e.g., `vi`) |
| `gender` | string | null | Filter by gender (`male`, `female`) |
| `engine` | string | null | Filter by engine (`edge`, `gtts`, `capcut`, `vivibe`) |

#### Available Voices

| Voice ID | Name | Engine | Gender | Description |
|----------|------|--------|--------|-------------|
| `vi-VN-HoaiMyNeural` | Edge Nữ | edge | female | Vietnamese female - natural and clear |
| `vi-VN-NamMinhNeural` | Edge Nam | edge | male | Vietnamese male - professional |
| `gtts-vi` | gTTS Nữ | gtts | female | Google TTS Vietnamese voice |
| `tt-BV074_streaming` | CapCut Nữ | capcut | female | CapCut/TikTok style female |
| `tt-BV075_streaming` | CapCut Nam | capcut | male | CapCut/TikTok style male |
| `cLZiqtzLcKYqwYrWJemAJH` | Vivibe Nữ | vivibe | female | Vivibe high-quality female voice |
| `6QzFMn95VAXF32Yg3HxEMj` | Vivibe Nam | vivibe | male | Vivibe high-quality male voice |

#### Response Example

```json
{
  "voices": [
    {
      "id": "vi-VN-HoaiMyNeural",
      "name": "Edge Nữ",
      "language": "vi-VN",
      "gender": "female",
      "engine": "edge",
      "description": "Vietnamese female voice - natural and clear"
    },
    {
      "id": "tt-BV074_streaming",
      "name": "CapCut Nữ",
      "language": "vi-VN",
      "gender": "female",
      "engine": "capcut",
      "description": "Vietnamese female voice - CapCut/TikTok style"
    }
  ]
}
```

---

### TTS Synthesize

**POST** `/tts/synthesize`

Synthesize text to speech. Returns audio as base64-encoded string.

#### Request Body (JSON)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `text` | string | *required* | 1-5000 chars | Text to convert to speech |
| `voice_id` | string | `vi-VN-HoaiMyNeural` | See [Voices](#available-voices) | Voice ID to use |
| `pitch` | int | `0` | `-12` to `+12` | Pitch adjustment in semitones |
| `speed` | float | `1.0` | `0.5` to `1.5` | Speed multiplier |
| `output_format` | string | `mp3` | `mp3`, `wav` | Output audio format |

#### Pitch Values

| Value | Effect |
|-------|--------|
| `-12` | Very deep voice (1 octave lower) |
| `-6` | Deep voice |
| `0` | Original voice |
| `+4` | Cute/higher voice |
| `+6` | High voice |
| `+12` | Very high voice (1 octave higher) |

#### Speed Values

| Value | Effect |
|-------|--------|
| `0.5` | Half speed (slower, longer audio) |
| `0.75` | Slightly slower |
| `1.0` | Normal speed |
| `1.25` | Slightly faster |
| `1.5` | 1.5x speed (faster, shorter audio) |

#### Request Example

```json
{
  "text": "Xin chào, tôi là trợ lý ảo.",
  "voice_id": "vi-VN-HoaiMyNeural",
  "pitch": 4,
  "speed": 1.0,
  "output_format": "mp3"
}
```

#### Response Example

```json
{
  "success": true,
  "audio": "<base64-encoded-audio-data>",
  "format": "mp3",
  "size_bytes": 12345,
  "voice_id": "vi-VN-HoaiMyNeural",
  "voice_name": "Edge Nữ",
  "engine": "edge",
  "pitch": 4,
  "speed": 1.0,
  "processing_time_ms": 1234.5
}
```

#### cURL Example

```bash
curl -X POST "http://localhost:8000/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào, tôi là trợ lý ảo.",
    "voice_id": "vi-VN-HoaiMyNeural",
    "pitch": 4,
    "speed": 1.0
  }' | jq -r '.audio' | base64 -d > output.mp3
```

---

### TTS Time Adjust

Automatically calculate speed to fit a target duration.

#### Additional Parameters for Time Adjust

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `target_duration_ms` | int | null | `100` to `60000` | Target duration in milliseconds |
| `min_speed` | float | null | `0.3` to `1.0` | Minimum speed limit |
| `max_speed` | float | null | `1.0` to `3.0` | Maximum speed limit |

When `target_duration_ms` is set:
1. Audio is first generated at normal speed (1.0x)
2. Original duration is measured
3. Required speed is calculated: `speed = original_duration / target_duration`
4. Speed is clamped to `min_speed` and `max_speed` if specified
5. Audio is regenerated at calculated speed

#### Request Example (Time Adjust)

```json
{
  "text": "Đây là một câu dài cần khớp vào 3 giây.",
  "voice_id": "vi-VN-HoaiMyNeural",
  "pitch": 0,
  "target_duration_ms": 3000,
  "min_speed": 0.5,
  "max_speed": 2.0
}
```

#### Response Example (Time Adjust)

```json
{
  "success": true,
  "audio": "<base64-encoded-audio>",
  "format": "mp3",
  "size_bytes": 12345,
  "voice_id": "vi-VN-HoaiMyNeural",
  "voice_name": "Edge Nữ",
  "engine": "edge",
  "pitch": 0,
  "speed": 1.35,
  "processing_time_ms": 2500.0,
  "time_adjust": {
    "target_duration_ms": 3000,
    "original_duration_ms": 4050,
    "calculated_speed": 1.35,
    "final_speed": 1.35,
    "speed_clamped": false,
    "min_speed": 0.5,
    "max_speed": 2.0
  }
}
```

---

### TTS Engines

**GET** `/tts/engines`

List available TTS engines.

#### Response Example

```json
{
  "engines": [
    {"name": "edge", "display_name": "Microsoft Edge TTS"},
    {"name": "gtts", "display_name": "Google TTS"},
    {"name": "capcut", "display_name": "CapCut TTS"},
    {"name": "vivibe", "display_name": "Vivibe TTS"}
  ],
  "available": true
}
```

#### Engine Comparison

| Engine | Quality | Speed | Voices | Notes |
|--------|---------|-------|--------|-------|
| **Edge TTS** | High | Fast | 2 (Nữ, Nam) | Natural neural voices |
| **CapCut TTS** | High | Fast | 2 (Nữ, Nam) | TikTok/CapCut style |
| **Vivibe TTS** | High | Fast | 2 (Nữ, Nam) | Custom voice cloning platform |
| **gTTS** | Good | Medium | 1 (Nữ) | Google Translate TTS |

#### Vivibe TTS Configuration

Vivibe TTS requires authentication token from the Vivibe/LucyLab platform.

**Environment Variable:**
```bash
# .env file
VIVIBE_TOKEN=your_jwt_token_here
```

**Or pass token in request:**
```json
{
  "text": "Xin chào",
  "voice_id": "cLZiqtzLcKYqwYrWJemAJH",
  "vivibe_token": "your_jwt_token_here"
}
```

> **Note:** JWT tokens from Firebase typically expire after 1 hour. Configure `VIVIBE_TOKEN` in `.env` for automatic token usage.

---

### TTS Raw Audio

**POST** `/tts/synthesize/audio`

Synthesize and return raw audio file (not base64 encoded).

Same parameters as `/tts/synthesize`.

Returns audio file with headers:
- `Content-Type`: `audio/mpeg` (mp3) or `audio/wav`
- `Content-Disposition`: `attachment; filename="tts_output.mp3"`

```bash
curl -X POST "http://localhost:8000/tts/synthesize/audio" \
  -H "Content-Type: application/json" \
  -d '{"text": "Xin chào", "voice_id": "vi-VN-HoaiMyNeural"}' \
  --output output.mp3
```

---

## Audio Separator

Separate vocals and instrumental from audio, then remix with custom volumes.

### Separator Submit

**POST** `/separator/`

Submit an audio separation job.

#### Request (multipart/form-data)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `audio_file` | File | *required* | Max 500MB | Audio file to process |
| `vocal_volume` | float | `1.0` | `0.0` to `3.0` | Vocal volume multiplier |
| `instrumental_volume` | float | `1.0` | `0.0` to `3.0` | Instrumental volume multiplier |
| `output_format` | string | `mp3` | `mp3`, `wav`, `flac` | Output audio format |
| `model` | string | `fast` | `fast`, `balanced`, `quality` | Separation model |

#### Volume Settings

| `vocal_volume` | `instrumental_volume` | Result |
|----------------|----------------------|--------|
| `0.0` | `1.0` | Karaoke (vocals removed) |
| `1.0` | `0.0` | Vocals only (acapella) |
| `0.5` | `1.0` | Vocals reduced by 50% |
| `1.5` | `1.0` | Vocals boosted by 50% |
| `1.0` | `1.5` | Instrumental boosted by 50% |

#### Supported Audio Formats

- MP3 (`.mp3`)
- WAV (`.wav`)
- M4A (`.m4a`)
- FLAC (`.flac`)
- OGG (`.ogg`)
- OPUS (`.opus`)
- WebM (`.webm`)

#### Response Example

```json
{
  "job_id": "abc12345",
  "status": "pending",
  "message": "Job submitted successfully"
}
```

#### cURL Example

```bash
# Create karaoke version (remove vocals)
curl -X POST "http://localhost:8000/separator/" \
  -F "audio_file=@song.mp3" \
  -F "vocal_volume=0.0" \
  -F "instrumental_volume=1.0" \
  -F "output_format=mp3" \
  -F "model=balanced"
```

---

### Separator Status

**GET** `/separator/jobs/{job_id}`

Get the status of a separation job.

#### Response (Processing)

```json
{
  "job_id": "abc12345",
  "status": "processing",
  "progress": 45
}
```

#### Response (Completed)

```json
{
  "job_id": "abc12345",
  "status": "completed",
  "progress": 100,
  "result": {
    "type": "audio",
    "format": "mp3",
    "filename": "song_mixed.mp3",
    "data": "<base64-encoded-audio>",
    "size_bytes": 1234567,
    "metadata": {
      "processing_time_ms": 15234.5,
      "vocal_volume": 0.0,
      "instrumental_volume": 1.0
    }
  }
}
```

#### Response (Failed)

```json
{
  "job_id": "abc12345",
  "status": "failed",
  "progress": 30,
  "error": "Failed to load audio file"
}
```

#### Job Status Values

| Status | Description |
|--------|-------------|
| `pending` | Job queued, waiting to start |
| `processing` | Job is being processed |
| `completed` | Job finished successfully |
| `failed` | Job failed with error |

---

### Separator Models

| Model | File | Time | Quality | Use Case |
|-------|------|------|---------|----------|
| `fast` | 1_HP-UVR.pth | ~5-10 sec | Decent | Quick preview |
| `balanced` | UVR_MDXNET_Main.onnx | ~20 sec | Good | General use |
| `quality` | htdemucs.yaml | ~2 min | Highest | Professional |

---

### List All Jobs

**GET** `/separator/jobs`

List all separation jobs.

```json
{
  "jobs": [
    {
      "job_id": "abc12345",
      "status": "completed",
      "progress": 100,
      "format": "mp3",
      "filename": "song.mp3",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Subtitle Generation (STT)

### STT Generate

**POST** `/subtitle`

Generate subtitle file (SRT) or transcription data (JSON) from audio.

#### Request Parameters (multipart/form-data)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `audio_file` | File | *required* | Audio file (MP3, WAV, M4A, FLAC, OGG, OPUS, WebM) |
| `format` | string | `srt` | Output format (`srt`, `json`) |
| `engine` | string | `faster-whisper` | ASR engine (`faster-whisper`, `openai-whisper`) |
| `model_size` | string | `large-v3` | Model size (see [Models](#stt-models)) |
| `compute_type` | string | auto | Quantization (`int8`, `float16`, `float32`) |
| `language` | string | auto | ISO 639-1 code (e.g., `en`, `zh`, `vi`) |
| `vad_filter` | bool | `true` | Enable voice activity detection |
| `word_timestamps` | bool | `true` | Include word-level timestamps |
| `batch_size` | int | `16` | Batch size (`1`-`64`) |
| `beam_size` | int | `5` | Beam search size (`1`-`20`) |
| `temperature` | float | `0.0` | Sampling temperature (`0.0`-`1.0`) |
| `best_of` | int | `5` | Best of N samples (OpenAI Whisper) |
| `condition_on_previous_text` | bool | `true` | Use previous segment as context |
| `no_speech_threshold` | float | `0.6` | No speech detection threshold |
| `compression_ratio_threshold` | float | `2.4` | Reject hallucinations threshold |
| `logprob_threshold` | float | `-1.0` | Reject low confidence threshold |
| `initial_prompt` | string | null | Initial prompt for context |

**SRT-only parameters:**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `word_level` | bool | `false` | - | One word per subtitle line |
| `max_line_width` | int | `42` | `10`-`100` | Max characters per line |
| `max_line_count` | int | `2` | `1`-`3` | Max lines per subtitle |
| `adjust_timing` | bool | `false` | - | Adjust timing for natural reading |

#### Response (format=srt)

```
1
00:00:00,000 --> 00:00:02,500
Hello world.

2
00:00:02,800 --> 00:00:05,200
This is a test.
```

#### Response (format=json)

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
  "metadata": {
    "engine": "faster-whisper",
    "model_size": "large-v3",
    "language": "en",
    "audio_duration_s": 120.5,
    "inference_time_ms": 15234.5,
    "total_time_ms": 16434.5,
    "real_time_factor": 0.14
  }
}
```

---

### ASR Engines

| Engine | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| `faster-whisper` | 4x faster | Good | Batch processing, long videos |
| `openai-whisper` | Normal | Best | High-quality dialogue, movies |

---

### STT Models

#### faster-whisper Models

| Model | VRAM | Speed | Use Case |
|-------|------|-------|----------|
| `tiny` | ~1GB | Fastest | Testing |
| `base` | ~1GB | Very Fast | Quick drafts |
| `small` | ~2GB | Fast | Balance |
| `medium` | ~5GB | Moderate | Good quality |
| `large-v2` | ~10GB | Slow | High quality |
| `large-v3` | ~10GB | Slow | Best quality |
| `distil-large-v3` | ~6GB | Fast | Quality + Speed |

#### openai-whisper Models

| Model | VRAM | Speed | Use Case |
|-------|------|-------|----------|
| `tiny`/`tiny.en` | ~1GB | Fastest | Testing |
| `base`/`base.en` | ~1GB | Very Fast | Quick drafts |
| `small`/`small.en` | ~2GB | Fast | Balance |
| `medium`/`medium.en` | ~5GB | Moderate | Good quality |
| `large`/`large-v2`/`large-v3` | ~10GB | Slow | Best quality |
| `turbo` | ~6GB | Fast | **Recommended** |

---

## Health & Metrics

### Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "uptime_seconds": 3600.0,
  "version": "4.0.0"
}
```

### Root Endpoint

**GET** `/`

```json
{
  "service": "Audio Processing Service",
  "version": "4.0.0",
  "status": "operational",
  "documentation": "/docs",
  "api_docs": "/redoc"
}
```

### Metrics

**GET** `/metrics`

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
| 404 | Not Found | Resource not found (e.g., voice, job) |
| 413 | file_too_large | File exceeds 500MB limit |
| 415 | unsupported_media_type | Invalid audio format |
| 422 | validation_error | Invalid parameters |
| 500 | Internal Server Error | Processing failed |
| 503 | Service Unavailable | Engine not available |
| 507 | insufficient_vram | Not enough GPU memory |

---

## Integration Examples

### Python - TTS

```python
import requests
import base64

# Synthesize speech
response = requests.post(
    "http://localhost:8000/tts/synthesize",
    json={
        "text": "Xin chào, tôi là trợ lý ảo.",
        "voice_id": "vi-VN-HoaiMyNeural",
        "pitch": 4,
        "speed": 1.0
    }
)

data = response.json()
if data["success"]:
    audio_bytes = base64.b64decode(data["audio"])
    with open("output.mp3", "wb") as f:
        f.write(audio_bytes)
```

### Python - Audio Separator

```python
import requests
import base64
import time

# Submit job
with open("song.mp3", "rb") as f:
    response = requests.post(
        "http://localhost:8000/separator/",
        files={"audio_file": f},
        data={
            "vocal_volume": 0.0,
            "instrumental_volume": 1.0,
            "model": "balanced"
        }
    )

job_id = response.json()["job_id"]

# Poll for completion
while True:
    status = requests.get(f"http://localhost:8000/separator/jobs/{job_id}").json()

    if status["status"] == "completed":
        audio_bytes = base64.b64decode(status["result"]["data"])
        with open("karaoke.mp3", "wb") as f:
            f.write(audio_bytes)
        break
    elif status["status"] == "failed":
        print(f"Error: {status['error']}")
        break

    time.sleep(2)
```

### JavaScript - TTS

```javascript
async function synthesizeSpeech(text, voiceId = "vi-VN-HoaiMyNeural") {
  const response = await fetch("http://localhost:8000/tts/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      voice_id: voiceId,
      pitch: 0,
      speed: 1.0
    })
  });

  const data = await response.json();

  if (data.success) {
    // Convert base64 to audio blob
    const audioData = atob(data.audio);
    const bytes = new Uint8Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      bytes[i] = audioData.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: "audio/mpeg" });

    // Play audio
    const audio = new Audio(URL.createObjectURL(blob));
    audio.play();
  }
}
```

---

## Rate Limits

- **Max file size:** 500MB
- **Request timeout:** 5 minutes (300 seconds)
- **Concurrent requests:** Limited by GPU memory
- **TTS max text length:** 5000 characters

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
