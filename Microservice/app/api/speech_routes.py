"""
Speech API Routes - Voice transcription endpoint.

Provides REST API for C# desktop app to send audio and get transcription.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.speech.voice_recognizer import get_voice_recognizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speech", tags=["speech"])


class TranscribeRequest(BaseModel):
    """Request model for speech transcription."""
    audio_base64: str  # Base64 encoded audio data
    format: str = "wav"  # Audio format (wav, mp3, webm)


class TranscribeResponse(BaseModel):
    """Response model for speech transcription."""
    text: str
    confidence: float
    source: Optional[str] = None
    error: Optional[str] = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio to text.
    
    Accepts base64-encoded audio (WAV preferred) and returns transcription.
    Uses Google Speech API with Sphinx fallback.
    
    Example:
        POST /api/speech/transcribe
        {
            "audio_base64": "UklGRi4A...",  // WAV audio
            "format": "wav"
        }
    
    Returns:
        {
            "text": "open notepad",
            "confidence": 0.9,
            "source": "google"
        }
    """
    logger.info(f"[SPEECH API] Transcribe request received ({len(request.audio_base64)} chars)")
    
    try:
        recognizer = get_voice_recognizer()
        result = await recognizer.transcribe_base64(request.audio_base64, request.format)
        
        if result.get("text"):
            logger.info(f"[SPEECH API] ✓ Transcribed: '{result['text']}'")
        else:
            logger.warning(f"[SPEECH API] ⚠ No transcription: {result.get('error', 'unknown')}")
        
        return TranscribeResponse(
            text=result.get("text", ""),
            confidence=result.get("confidence", 0),
            source=result.get("source"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"[SPEECH API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def speech_health():
    """Health check for speech service."""
    from app.speech.voice_recognizer import SR_AVAILABLE
    return {
        "status": "ok" if SR_AVAILABLE else "degraded",
        "speech_recognition_available": SR_AVAILABLE
    }
