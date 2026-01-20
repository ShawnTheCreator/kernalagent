"""
Voice Recognition Service - Python-based speech-to-text.

Uses the SpeechRecognition library with FREE Google Web Speech API.
No API keys required - this is the same free service Chrome uses.
"""

import os
import base64
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import speech recognition library
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
    logger.info("[VOICE] speech_recognition library available")
except ImportError:
    SR_AVAILABLE = False
    logger.warning("[VOICE] speech_recognition not installed - run: pip install SpeechRecognition")


class VoiceRecognizer:
    """
    Voice recognition using SpeechRecognition library.
    
    Uses FREE Google Web Speech API (no API key needed).
    This is the same speech recognition that Chrome uses.
    """
    
    def __init__(self):
        if SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
            # Adjust for ambient noise threshold
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            logger.info("[VOICE] ✓ VoiceRecognizer initialized")
        else:
            self.recognizer = None
            logger.warning("[VOICE] ✗ VoiceRecognizer unavailable")
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        format: str = "wav",
        language: str = "en-US"
    ) -> dict:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Raw audio bytes (WAV format preferred)
            format: Audio format (wav, mp3, webm)
            language: Language code (en-US, en-IN, etc.)
            
        Returns:
            dict with 'text', 'confidence', 'error'
        """
        if not SR_AVAILABLE:
            return {
                "text": "", 
                "confidence": 0, 
                "error": "speech_recognition not installed. Run: pip install SpeechRecognition"
            }
        
        if self.recognizer is None:
            return {"text": "", "confidence": 0, "error": "Recognizer not initialized"}
        
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            try:
                # Load audio using speech_recognition
                with sr.AudioFile(temp_path) as source:
                    # Adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = self.recognizer.record(source)
                
                # Use FREE Google Web Speech API (no API key needed!)
                # This is the same API that powers Chrome's speech recognition
                try:
                    text = self.recognizer.recognize_google(audio, language=language)
                    logger.info(f"[VOICE] ✓ Transcribed: '{text}'")
                    return {
                        "text": text, 
                        "confidence": 0.9, 
                        "source": "google_free",
                        "language": language
                    }
                except sr.UnknownValueError:
                    logger.warning("[VOICE] Could not understand audio")
                    return {"text": "", "confidence": 0, "error": "Could not understand audio"}
                except sr.RequestError as e:
                    logger.error(f"[VOICE] Google API error: {e}")
                    return {"text": "", "confidence": 0, "error": f"Speech API error: {e}"}
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"[VOICE] Transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return {"text": "", "confidence": 0, "error": str(e)}
    
    async def transcribe_base64(
        self, 
        audio_base64: str, 
        format: str = "wav",
        language: str = "en-US"
    ) -> dict:
        """
        Transcribe base64-encoded audio.
        
        Args:
            audio_base64: Base64 encoded audio data
            format: Audio format
            language: Language code
            
        Returns:
            dict with transcription result
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"[VOICE] Received {len(audio_bytes)} bytes of audio")
            return await self.transcribe_audio(audio_bytes, format, language)
        except Exception as e:
            logger.error(f"[VOICE] Base64 decode failed: {e}")
            return {"text": "", "confidence": 0, "error": f"Invalid base64: {e}"}


# Singleton instance
_voice_recognizer: Optional[VoiceRecognizer] = None


def get_voice_recognizer() -> VoiceRecognizer:
    """Get the singleton VoiceRecognizer instance."""
    global _voice_recognizer
    if _voice_recognizer is None:
        _voice_recognizer = VoiceRecognizer()
    return _voice_recognizer
