"""
TTS API Router

API endpoints for Text-to-Speech synthesis.
"""

import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class TTSSynthesizeRequest(BaseModel):
    """Request body for TTS synthesis."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice_id: str = Field(default="vi-VN-HoaiMyNeural", description="Voice ID to use")
    pitch: int = Field(default=0, ge=-12, le=12, description="Pitch adjustment in semitones (-12 to +12)")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speed multiplier (0.5 to 2.0)")
    output_format: str = Field(default="mp3", description="Output format (mp3 or wav)")


class VoiceResponse(BaseModel):
    """Voice information response."""
    id: str
    name: str
    language: str
    gender: str
    engine: str
    description: str


@router.get("/voices", tags=["TTS"])
async def list_voices(
    language: Optional[str] = Query(None, description="Filter by language (e.g., 'vi')"),
    gender: Optional[str] = Query(None, description="Filter by gender (male, female)"),
    engine: Optional[str] = Query(None, description="Filter by engine (edge, gtts)"),
):
    """
    List available TTS voices.

    **Example Response:**
    ```json
    {
        "voices": [
            {
                "id": "vi-VN-HoaiMyNeural",
                "name": "Hoai My",
                "language": "vi-VN",
                "gender": "female",
                "engine": "edge",
                "description": "Vietnamese female voice - natural and clear"
            }
        ]
    }
    ```
    """
    from modules.tts import get_tts_service
    from modules.tts.engines.base import VoiceGender

    service = get_tts_service()

    # Parse gender filter
    gender_filter = None
    if gender:
        gender_lower = gender.lower()
        if gender_lower == "male":
            gender_filter = VoiceGender.MALE
        elif gender_lower == "female":
            gender_filter = VoiceGender.FEMALE

    voices = service.list_voices(
        language=language,
        gender=gender_filter,
        engine=engine,
    )

    return JSONResponse(content={
        "voices": [v.to_dict() for v in voices]
    })


@router.get("/engines", tags=["TTS"])
async def list_engines():
    """
    List available TTS engines.

    **Example Response:**
    ```json
    {
        "engines": [
            {"name": "edge", "display_name": "Microsoft Edge TTS"},
            {"name": "gtts", "display_name": "Google TTS"}
        ]
    }
    ```
    """
    from modules.tts import get_tts_service

    service = get_tts_service()
    engines = service.list_engines()

    return JSONResponse(content={
        "engines": engines,
        "available": service.is_available(),
    })


@router.post("/synthesize", tags=["TTS"])
async def synthesize(request: TTSSynthesizeRequest):
    """
    Synthesize text to speech.

    Returns audio data as base64-encoded string.

    **Parameters:**
    - `text`: Text to convert to speech (max 5000 chars)
    - `voice_id`: Voice to use (see /tts/voices for options)
    - `pitch`: Pitch adjustment in semitones (-12 to +12, default 0)
    - `speed`: Speed multiplier (0.5 to 2.0, default 1.0)
    - `output_format`: Output format (mp3 or wav)

    **Example Request:**
    ```json
    {
        "text": "Xin chào, tôi là trợ lý ảo.",
        "voice_id": "vi-VN-HoaiMyNeural",
        "pitch": 4,
        "speed": 1.0
    }
    ```

    **Example Response:**
    ```json
    {
        "success": true,
        "audio": "<base64-encoded-audio>",
        "format": "mp3",
        "voice_id": "vi-VN-HoaiMyNeural",
        "voice_name": "Hoai My",
        "engine": "edge",
        "pitch": 4,
        "speed": 1.0,
        "processing_time_ms": 1234.5
    }
    ```
    """
    from modules.tts import get_tts_service, TTSRequest

    service = get_tts_service()

    if not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No TTS engine available. Install edge-tts or gTTS."
        )

    # Validate voice exists
    voice = service.get_voice(request.voice_id)
    if not voice:
        available_voices = [v.id for v in service.list_voices()]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "voice_not_found",
                "message": f"Voice '{request.voice_id}' not found",
                "available_voices": available_voices,
            }
        )

    # Create TTS request
    tts_request = TTSRequest(
        text=request.text,
        voice_id=request.voice_id,
        pitch=request.pitch,
        speed=request.speed,
        output_format=request.output_format,
    )

    # Synthesize
    result = await service.synthesize(tts_request)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "synthesis_failed",
                "message": result.error,
            }
        )

    # Encode audio as base64
    audio_base64 = base64.b64encode(result.audio_data).decode("utf-8")

    return JSONResponse(content={
        "success": True,
        "audio": audio_base64,
        "format": result.format,
        "size_bytes": len(result.audio_data),
        "voice_id": result.voice_id,
        "voice_name": result.voice_name,
        "engine": result.engine,
        "pitch": result.pitch,
        "speed": result.speed,
        "processing_time_ms": result.processing_time_ms,
    })


@router.post("/synthesize/audio", tags=["TTS"])
async def synthesize_audio(request: TTSSynthesizeRequest):
    """
    Synthesize text to speech and return raw audio.

    Returns audio file directly (not base64 encoded).

    **Content-Type:** audio/mpeg (mp3) or audio/wav
    """
    from modules.tts import get_tts_service, TTSRequest

    service = get_tts_service()

    if not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No TTS engine available"
        )

    # Create TTS request
    tts_request = TTSRequest(
        text=request.text,
        voice_id=request.voice_id,
        pitch=request.pitch,
        speed=request.speed,
        output_format=request.output_format,
    )

    # Synthesize
    result = await service.synthesize(tts_request)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )

    # Return raw audio
    content_type = "audio/mpeg" if result.format == "mp3" else "audio/wav"
    return Response(
        content=result.audio_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="tts_output.{result.format}"'
        }
    )


@router.get("/presets", tags=["TTS"])
async def get_presets():
    """
    Get predefined voice presets.

    Presets are voice + pitch combinations for common use cases.

    **Example Response:**
    ```json
    {
        "presets": [
            {
                "id": "hoaimy_default",
                "name": "Hoai My (Default)",
                "voice_id": "vi-VN-HoaiMyNeural",
                "pitch": 0,
                "speed": 1.0,
                "description": "Natural female voice"
            }
        ]
    }
    ```
    """
    presets = [
        {
            "id": "hoaimy_default",
            "name": "Hoai My (Default)",
            "voice_id": "vi-VN-HoaiMyNeural",
            "pitch": 0,
            "speed": 1.0,
            "description": "Natural female voice",
        },
        {
            "id": "hoaimy_cute",
            "name": "Hoai My (Cute)",
            "voice_id": "vi-VN-HoaiMyNeural",
            "pitch": 4,
            "speed": 1.0,
            "description": "Higher pitch, cute female voice",
        },
        {
            "id": "namminh_default",
            "name": "Nam Minh (Default)",
            "voice_id": "vi-VN-NamMinhNeural",
            "pitch": 0,
            "speed": 1.0,
            "description": "Natural male voice",
        },
        {
            "id": "namminh_cute",
            "name": "Nam Minh (Cute)",
            "voice_id": "vi-VN-NamMinhNeural",
            "pitch": 6,
            "speed": 1.05,
            "description": "Higher pitch, cute male voice",
        },
        {
            "id": "gtts_default",
            "name": "Google TTS (Default)",
            "voice_id": "gtts-vi",
            "pitch": 0,
            "speed": 1.0,
            "description": "Google Vietnamese voice",
        },
        {
            "id": "gtts_cute",
            "name": "Google TTS (Cute)",
            "voice_id": "gtts-vi",
            "pitch": 4,
            "speed": 1.0,
            "description": "Higher pitch Google voice",
        },
    ]

    return JSONResponse(content={"presets": presets})
