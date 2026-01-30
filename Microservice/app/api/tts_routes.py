"""
TTS (Text-to-Speech) API routes using Edge TTS.
Provides /api/tts/speak endpoint for generating speech from text.
"""

import asyncio
import hashlib
import io
import logging
from pathlib import Path
from typing import Optional

import edge_tts
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])

# Simple in-memory cache for audio (text+voice -> audio bytes)
_audio_cache: dict[str, bytes] = {}
_cache_max_size = 100  # Keep last 100 unique requests


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-GuyNeural"  # Default voice
    rate: Optional[str] = "0%"  # Speaking rate
    volume: Optional[str] = "0%"  # Volume
    pitch: Optional[str] = "0Hz"  # Pitch


def _normalize_percent(value: Optional[str]) -> str:
    if not value:
        return "+0%"
    v = value.strip()
    if v.endswith("%") and len(v) > 1 and (v[0].isdigit()):
        return f"+{v}"
    return v


def _normalize_pitch(value: Optional[str]) -> str:
    if not value:
        return "+0Hz"
    v = value.strip()
    if v.lower().endswith("hz") and len(v) > 2 and (v[0].isdigit()):
        return f"+{v}"
    return v


def _cache_key(text: str, voice: str, rate: str, volume: str, pitch: str) -> str:
    """Generate cache key from request parameters."""
    key_str = f"{text}|{voice}|{rate}|{volume}|{pitch}"
    return hashlib.sha256(key_str.encode()).hexdigest()


def _cleanup_cache():
    """Simple LRU cleanup: keep only last N items."""
    global _audio_cache
    if len(_audio_cache) > _cache_max_size:
        # Remove oldest entries (simple approach: keep last half)
        keys_to_remove = list(_audio_cache.keys())[: _cache_max_size // 2]
        for k in keys_to_remove:
            del _audio_cache[k]
        logger.info(f"[TTS] Cache cleanup: removed {len(keys_to_remove)} old entries")


@router.post("/speak")
async def speak(request: SpeakRequest):
    """
    Generate speech from text using Edge TTS.
    
    Returns audio as streaming MP3.
    """
    try:
        # Check cache first
        cache_key = _cache_key(
            request.text, request.voice, request.rate, request.volume, request.pitch
        )
        if cache_key in _audio_cache:
            logger.info(f"[TTS] Cache hit for: {request.text[:50]}...")
            audio_bytes = _audio_cache[cache_key]
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=speech.mp3"},
            )

        rate = _normalize_percent(request.rate)
        volume = _normalize_percent(request.volume)
        pitch = _normalize_pitch(request.pitch)

        # Generate speech with Edge TTS
        logger.info(f"[TTS] Generating speech for: {request.text[:50]}...")
        communicate = edge_tts.Communicate(
            text=request.text,
            voice=request.voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )

        # Create MP3 in memory
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        # Cache the result
        _audio_cache[cache_key] = audio_data
        _cleanup_cache()

        logger.info(f"[TTS] Generated {len(audio_data)} bytes of audio")
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )

    except Exception as e:
        logger.error(f"[TTS] Error generating speech: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@router.get("/voices")
async def list_voices():
    """List available Edge TTS voices."""
    try:
        voices = await edge_tts.list_voices()
        # Filter to useful fields and sort by locale
        filtered = [
            {
                "name": v["Name"],
                "locale": v["Locale"],
                "gender": v["Gender"],
                "sample_rate": v.get("SampleRateHertz", "Unknown"),
            }
            for v in voices
        ]
        return {"voices": sorted(filtered, key=lambda x: x["locale"])}
    except Exception as e:
        logger.error(f"[TTS] Error listing voices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {str(e)}")


@router.delete("/cache")
async def clear_cache():
    """Clear the audio cache."""
    global _audio_cache
    _audio_cache.clear()
    logger.info("[TTS] Audio cache cleared")
    return {"message": "Audio cache cleared"}
