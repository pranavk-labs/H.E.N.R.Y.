"""Speech-to-text (STT) service with OpenAI Whisper support (free, open-source, offline).

Supported engines:
- "none": raise if transcribe is called (default)
- "dummy": return empty string for development
- "whisper": use OpenAI Whisper - requires openai-whisper package
"""

from __future__ import annotations

from typing import Optional
import logging
import io
import numpy as np

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Speech-to-text (STT) service with Whisper support."""

    _instance: Optional["SpeechToTextService"] = None
    silence_threshold = 0.001

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = getattr(settings, "stt_engine", "none")
        self._whisper_model = None

        if self.engine == "whisper":
            try:
                import whisper

                # Load model (tiny, base, small, medium, large)
                # For server, recommend "small" for better accuracy or "base" for speed
                model_size = getattr(settings, "whisper_model_size", "small")
                device = getattr(settings, "whisper_device", "cpu")
                if device:
                    logger.info(f"Loading OpenAI Whisper model: {model_size} on {device}")
                    self._whisper_model = whisper.load_model(model_size, device=device)
                else:
                    logger.info(f"Loading OpenAI Whisper model: {model_size}")
                    self._whisper_model = whisper.load_model(model_size)
                logger.info("OpenAI Whisper model loaded successfully")
            except ImportError:
                logger.warning(
                    "openai-whisper not available. Install with: poetry install --extras server"
                )
                self.engine = "none"
            except Exception as e:
                logger.error(f"Failed to load OpenAI Whisper model: {e}")
                self.engine = "none"

    @classmethod
    def get_instance(cls) -> "SpeechToTextService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(get_settings())
        return cls._instance

    @classmethod
    def is_silent_pcm16(cls, audio_bytes: bytes) -> bool:
        """Return whether PCM int16 audio is empty or effectively silent."""
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        if audio_array.size == 0:
            return True
        peak = int(np.max(np.abs(audio_array.astype(np.int32))))
        return peak < int(cls.silence_threshold * 32768)

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        """Convert raw audio bytes into text.

        Args:
            audio_bytes: PCM audio data (int16 format expected).
            sample_rate: Sample rate of the audio (Hz).

        Returns:
            Transcribed text.
        """
        if self.engine == "dummy":
            logger.info("SpeechToTextService(dummy): returning placeholder text")
            return ""

        if self.engine == "whisper" and self._whisper_model is not None:
            try:
                # Convert bytes to numpy array (int16)
                audio_array = (
                    np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                )
                if self.is_silent_pcm16(audio_bytes):
                    logger.info("OpenAI Whisper transcription skipped for silent audio")
                    return ""

                # OpenAI Whisper expects 16kHz audio
                # Transcribe using OpenAI Whisper
                result = self._whisper_model.transcribe(
                    audio_array,
                    language="en",  # Can be None for auto-detect
                    fp16=False,  # Use FP32 for CPU compatibility
                )
                text = result.get("text", "").strip()
                logger.info(f"OpenAI Whisper transcription: {text}")
                return text
            except Exception as e:
                logger.error(f"OpenAI Whisper transcription failed: {e}")
                return ""

        raise RuntimeError(
            f"Speech-to-text engine '{self.engine}' is not configured or available. "
            "Set STT_ENGINE=whisper (requires: poetry install --extras server) or "
            "STT_ENGINE=dummy (for development placeholder)."
        )


__all__ = ["SpeechToTextService"]
