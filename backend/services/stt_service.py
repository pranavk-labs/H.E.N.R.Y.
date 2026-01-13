"""Speech-to-text (STT) service with Whisper support (free, open-source, offline).

Supported engines:
- "none": raise if transcribe is called (default)
- "dummy": return empty string for development
- "whisper": use OpenAI Whisper (free, open-source, offline) - requires openai-whisper package
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

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = getattr(settings, "stt_engine", "none")
        self._whisper_model = None

        if self.engine == "whisper":
            try:
                import whisper

                # Load base model (balanced speed/accuracy; can use "tiny" or "base" for faster)
                # Models: tiny, base, small, medium, large
                # For Pi, recommend "tiny" or "base" for speed, "small" for better accuracy
                model_size = getattr(settings, "whisper_model_size", "base")
                logger.info(f"Loading Whisper model: {model_size}")
                self._whisper_model = whisper.load_model(model_size)
                logger.info("Whisper model loaded successfully")
            except ImportError:
                logger.warning(
                    "Whisper not available. Install with: poetry add openai-whisper"
                )
                self.engine = "none"
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                self.engine = "none"

    @classmethod
    def get_instance(cls) -> "SpeechToTextService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(get_settings())
        return cls._instance

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
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(
                    np.float32
                ) / 32768.0

                # Whisper expects 16kHz, but we'll let it handle resampling if needed
                # Transcribe using Whisper
                result = self._whisper_model.transcribe(
                    audio_array,
                    fp16=False,  # Use fp32 for Pi compatibility
                    language="en",  # Can be None for auto-detect
                )
                text = result["text"].strip()
                logger.info(f"Whisper transcription: {text}")
                return text
            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}")
                return ""

        raise RuntimeError(
            f"Speech-to-text engine '{self.engine}' is not configured or available. "
            "Set STT_ENGINE=whisper (requires: poetry add openai-whisper) or "
            "STT_ENGINE=dummy (for development placeholder)."
        )


__all__ = ["SpeechToTextService"]


