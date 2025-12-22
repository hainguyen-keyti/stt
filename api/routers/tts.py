"""
TTS API Router

API endpoints for Text-to-Speech synthesis.
"""

import base64
import logging
import os
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
    speed: float = Field(default=1.0, ge=0.5, le=1.5, description="Speed multiplier (0.5 to 1.5)")
    output_format: str = Field(default="mp3", description="Output format (mp3 or wav)")

    # Time-based speed adjustment (optional)
    target_duration_ms: Optional[int] = Field(
        default=None,
        ge=100,
        le=60000,
        description="Target duration in milliseconds. If set, speed will be auto-calculated to fit this duration."
    )
    min_speed: Optional[float] = Field(
        default=None,
        ge=0.3,
        le=1.0,
        description="Minimum speed limit when using target_duration_ms (default: no limit)"
    )
    max_speed: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=3.0,
        description="Maximum speed limit when using target_duration_ms (default: no limit)"
    )


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

    # Determine speed - either direct speed value or calculate from target_duration_ms
    final_speed = request.speed
    calculated_speed = None
    original_duration_ms = None
    speed_clamped = False

    if request.target_duration_ms:
        # First, generate audio at normal speed (1.0) to get the natural duration
        tts_request_normal = TTSRequest(
            text=request.text,
            voice_id=request.voice_id,
            pitch=request.pitch,
            speed=1.0,
            output_format=request.output_format,
        )
        result_normal = await service.synthesize(tts_request_normal)

        if not result_normal.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "synthesis_failed",
                    "message": result_normal.error,
                }
            )

        # Get duration of the normal-speed audio
        from pydub import AudioSegment

        # Save to temp file to read duration
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(result_normal.audio_data)
            tmp_path = tmp.name

        try:
            audio = AudioSegment.from_mp3(tmp_path)
            original_duration_ms = len(audio)
        finally:
            os.unlink(tmp_path)

        # Calculate required speed: speed = original_duration / target_duration
        calculated_speed = original_duration_ms / request.target_duration_ms

        # Apply speed limits if specified
        final_speed = calculated_speed
        if request.min_speed and final_speed < request.min_speed:
            final_speed = request.min_speed
            speed_clamped = True
        if request.max_speed and final_speed > request.max_speed:
            final_speed = request.max_speed
            speed_clamped = True

    # Create TTS request with final speed
    tts_request = TTSRequest(
        text=request.text,
        voice_id=request.voice_id,
        pitch=request.pitch,
        speed=final_speed,
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

    # Build response
    response_data = {
        "success": True,
        "audio": audio_base64,
        "format": result.format,
        "size_bytes": len(result.audio_data),
        "voice_id": result.voice_id,
        "voice_name": result.voice_name,
        "engine": result.engine,
        "pitch": result.pitch,
        "speed": final_speed,
        "processing_time_ms": result.processing_time_ms,
    }

    # Add time adjustment info if used
    if request.target_duration_ms:
        response_data["time_adjust"] = {
            "target_duration_ms": request.target_duration_ms,
            "original_duration_ms": original_duration_ms,
            "calculated_speed": round(calculated_speed, 3) if calculated_speed else None,
            "final_speed": round(final_speed, 3),
            "speed_clamped": speed_clamped,
            "min_speed": request.min_speed,
            "max_speed": request.max_speed,
        }

    return JSONResponse(content=response_data)


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
