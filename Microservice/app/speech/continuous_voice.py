"""
Continuous Voice Recognition Service with Vosk.

Features:
- Continuous background listening using speech_recognition's listen_in_background()
- Offline speech recognition via Vosk (no internet required)
- Wake word detection: "hey kernel", "kernel"
- Stop word detection: "stop bud", "stop", "cancel"
- Automatic silence detection and command submission
- Real-time partial transcription callbacks
"""

import os
import json
import logging
import threading
import time
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Check for required libraries
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("[VOICE] speech_recognition not installed. Run: pip install SpeechRecognition")

try:
    from vosk import Model, KaldiRecognizer
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("[VOICE] vosk not installed. Run: pip install vosk")


class VoiceState(Enum):
    """Voice recognition state machine."""
    IDLE = "idle"           # Waiting for wake word
    LISTENING = "listening" # Actively capturing command
    PROCESSING = "processing"  # Processing command
    STOPPED = "stopped"     # Manually stopped


@dataclass
class VoiceConfig:
    """Configuration for continuous voice recognition."""
    wake_words: List[str] = None
    stop_words: List[str] = None
    silence_timeout_sec: float = 1.5  # Auto-submit after this silence
    always_listening: bool = True     # If False, requires wake word
    language: str = "en-us"
    
    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = ["hey kernel", "kernel", "hey colonel", "colonel"]
        if self.stop_words is None:
            self.stop_words = ["stop bud", "stop but", "stop", "cancel", "never mind"]


class ContinuousVoiceRecognizer:
    """
    Continuous voice recognition with wake/stop word detection.
    
    Uses speech_recognition library with Vosk for offline recognition.
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.state = VoiceState.IDLE
        self._stop_listening_func = None
        self._current_transcript = ""
        self._last_speech_time = time.time()
        self._silence_timer: Optional[threading.Timer] = None
        
        # Callbacks
        self.on_transcription: Optional[Callable[[str, bool], None]] = None  # (text, is_final)
        self.on_command: Optional[Callable[[str], None]] = None  # Final command to execute
        self.on_wake_word: Optional[Callable[[], None]] = None
        self.on_stop_word: Optional[Callable[[], None]] = None
        self.on_state_change: Optional[Callable[[VoiceState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Initialize recognizer
        if SR_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 0.8  # Seconds of silence to consider phrase complete
                self.microphone = sr.Microphone()
                logger.info("[VOICE] ✓ ContinuousVoiceRecognizer initialized with microphone")
            except Exception as e:
                # PyAudio not installed or microphone not available
                self.recognizer = sr.Recognizer()
                self.microphone = None
                logger.warning(f"[VOICE] Microphone not available (PyAudio not installed?): {e}")
                logger.warning("[VOICE] Voice recognition will be limited. Install PyAudio for full support.")
        else:
            self.recognizer = None
            self.microphone = None
            logger.error("[VOICE] ✗ speech_recognition not available")
        
        # Initialize Vosk model path
        self._vosk_model_path = self._find_vosk_model()
    
    def _find_vosk_model(self) -> Optional[str]:
        """Find Vosk model in common locations."""
        # Common model locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "vosk-model-small-en-us-0.15"),
            os.path.join(os.path.dirname(__file__), "model"),
            os.path.expanduser("~/.vosk/vosk-model-small-en-us-0.15"),
            "vosk-model-small-en-us-0.15",
            "model",
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                logger.info(f"[VOICE] Found Vosk model at: {path}")
                return path
        
        logger.warning("[VOICE] Vosk model not found. Will fall back to Google API.")
        return None
    
    def _set_state(self, new_state: VoiceState):
        """Update state and notify callback."""
        if self.state != new_state:
            logger.info(f"[VOICE] State: {self.state.value} → {new_state.value}")
            self.state = new_state
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains a wake word."""
        text_lower = text.lower().strip()
        for wake_word in self.config.wake_words:
            if wake_word in text_lower:
                return True
        return False
    
    def _check_stop_word(self, text: str) -> bool:
        """Check if text contains a stop word."""
        text_lower = text.lower().strip()
        for stop_word in self.config.stop_words:
            if stop_word in text_lower:
                return True
        return False
    
    def _remove_wake_word(self, text: str) -> str:
        """Remove wake word from the beginning of text."""
        text_lower = text.lower()
        for wake_word in sorted(self.config.wake_words, key=len, reverse=True):
            if text_lower.startswith(wake_word):
                return text[len(wake_word):].strip()
        return text
    
    def _audio_callback(self, recognizer, audio):
        """Callback for each audio chunk captured."""
        try:
            # Try Vosk first (offline)
            if VOSK_AVAILABLE and self._vosk_model_path:
                try:
                    text = recognizer.recognize_vosk(audio, language=self.config.language)
                    result = json.loads(text)
                    recognized_text = result.get("text", "").strip()
                except Exception as e:
                    logger.debug(f"[VOICE] Vosk failed, trying Google: {e}")
                    recognized_text = None
            else:
                recognized_text = None
            
            # Fall back to Google (online) if Vosk failed
            if not recognized_text:
                try:
                    recognized_text = recognizer.recognize_google(audio, language=self.config.language)
                except sr.UnknownValueError:
                    return  # No speech detected
                except sr.RequestError as e:
                    logger.error(f"[VOICE] Google API error: {e}")
                    if self.on_error:
                        self.on_error(f"Speech API error: {e}")
                    return
            
            if not recognized_text:
                return
            
            logger.info(f"[VOICE] Recognized: '{recognized_text}'")
            self._last_speech_time = time.time()
            
            # State machine logic
            if self.state == VoiceState.IDLE:
                # Check for wake word
                if self.config.always_listening or self._check_wake_word(recognized_text):
                    self._set_state(VoiceState.LISTENING)
                    if self.on_wake_word:
                        self.on_wake_word()
                    
                    # Remove wake word from text
                    command_text = self._remove_wake_word(recognized_text)
                    if command_text:
                        self._current_transcript = command_text
                        if self.on_transcription:
                            self.on_transcription(command_text, False)
                        self._start_silence_timer()
                    return
            
            elif self.state == VoiceState.LISTENING:
                # Check for stop word
                if self._check_stop_word(recognized_text):
                    logger.info("[VOICE] Stop word detected!")
                    self._cancel_silence_timer()
                    self._current_transcript = ""
                    self._set_state(VoiceState.IDLE)
                    if self.on_stop_word:
                        self.on_stop_word()
                    return
                
                # Accumulate transcript
                if self._current_transcript:
                    self._current_transcript += " " + recognized_text
                else:
                    self._current_transcript = recognized_text
                
                # Send partial transcription
                if self.on_transcription:
                    self.on_transcription(self._current_transcript, False)
                
                # Reset silence timer
                self._start_silence_timer()
        
        except Exception as e:
            logger.error(f"[VOICE] Audio callback error: {e}")
            import traceback
            traceback.print_exc()
            if self.on_error:
                self.on_error(str(e))
    
    def _start_silence_timer(self):
        """Start/reset the silence detection timer."""
        self._cancel_silence_timer()
        self._silence_timer = threading.Timer(
            self.config.silence_timeout_sec, 
            self._on_silence_timeout
        )
        self._silence_timer.start()
    
    def _cancel_silence_timer(self):
        """Cancel the silence detection timer."""
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None
    
    def _on_silence_timeout(self):
        """Called when silence is detected - submit the command."""
        if self.state == VoiceState.LISTENING and self._current_transcript:
            logger.info(f"[VOICE] Silence detected, submitting: '{self._current_transcript}'")
            
            # Send final transcription
            if self.on_transcription:
                self.on_transcription(self._current_transcript, True)
            
            # Submit command
            if self.on_command:
                self._set_state(VoiceState.PROCESSING)
                self.on_command(self._current_transcript)
            
            # Reset for next command
            self._current_transcript = ""
            self._set_state(VoiceState.IDLE if self.config.always_listening else VoiceState.IDLE)
    
    def start(self):
        """Start continuous voice recognition."""
        if not SR_AVAILABLE:
            logger.error("[VOICE] Cannot start - speech_recognition not available")
            return False
        
        if self.microphone is None:
            logger.error("[VOICE] Cannot start - microphone not available (PyAudio not installed)")
            if self.on_error:
                self.on_error("Microphone not available - PyAudio not installed for Python 3.14")
            return False
        
        if self._stop_listening_func:
            logger.warning("[VOICE] Already listening")
            return True
        
        try:
            # Adjust for ambient noise first
            with self.microphone as source:
                logger.info("[VOICE] Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Start background listening
            self._stop_listening_func = self.recognizer.listen_in_background(
                self.microphone, 
                self._audio_callback,
                phrase_time_limit=10  # Max 10 seconds per phrase
            )
            
            self._set_state(VoiceState.IDLE if not self.config.always_listening else VoiceState.LISTENING)
            logger.info("[VOICE] ✓ Continuous voice recognition started")
            return True
            
        except Exception as e:
            logger.error(f"[VOICE] Failed to start: {e}")
            if self.on_error:
                self.on_error(f"Failed to start voice recognition: {e}")
            return False
    
    def stop(self):
        """Stop continuous voice recognition."""
        self._cancel_silence_timer()
        
        if self._stop_listening_func:
            self._stop_listening_func(wait_for_stop=False)
            self._stop_listening_func = None
            logger.info("[VOICE] Continuous voice recognition stopped")
        
        self._set_state(VoiceState.STOPPED)
        self._current_transcript = ""
    
    def is_listening(self) -> bool:
        """Check if currently listening."""
        return self._stop_listening_func is not None
    
    def get_state(self) -> VoiceState:
        """Get current voice state."""
        return self.state


# Singleton instance
_continuous_recognizer: Optional[ContinuousVoiceRecognizer] = None


def get_continuous_recognizer(config: Optional[VoiceConfig] = None) -> ContinuousVoiceRecognizer:
    """Get the singleton ContinuousVoiceRecognizer instance."""
    global _continuous_recognizer
    if _continuous_recognizer is None:
        _continuous_recognizer = ContinuousVoiceRecognizer(config)
    return _continuous_recognizer
