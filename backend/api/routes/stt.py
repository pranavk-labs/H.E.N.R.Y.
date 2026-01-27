"""Speech-to-text API endpoints."""

from __future__ import annotations

import base64
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.stt_service import SpeechToTextService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stt", tags=["stt"])


class TranscribeRequest(BaseModel):
    """Request model for transcription."""

    audio_data: str = Field(
        ..., description="Base64-encoded audio data (PCM int16 format)"
    )
    sample_rate: int = Field(default=16000, description="Sample rate in Hz")


class TranscribeResponse(BaseModel):
    """Response model for transcription."""

    text: str = Field(..., description="Transcribed text")
    language: Optional[str] = Field(
        default="en", description="Detected or specified language"
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest) -> Any:
    """Transcribe audio to text.

    Args:
        req: Transcription request with base64-encoded audio

    Returns:
        Transcribed text and language

    Raises:
        HTTPException: If transcription fails
    """
    try:
        # Decode base64 audio data
        audio_bytes = base64.b64decode(req.audio_data)
    except Exception as e:
        logger.error(f"Failed to decode base64 audio: {e}")
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")

    try:
        # Get STT service and transcribe
        stt_service = SpeechToTextService.get_instance()
        text = stt_service.transcribe(audio_bytes, req.sample_rate)

        if not text:
            logger.warning("Transcription returned empty text")
            return TranscribeResponse(text="", language="en")

        logger.info(f"Successfully transcribed: {text}")
        return TranscribeResponse(text=text, language="en")

    except RuntimeError as e:
        # STT engine not configured
        logger.error(f"STT engine error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Transcription failed")
