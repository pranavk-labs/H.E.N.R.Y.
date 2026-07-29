"""Text-to-speech (TTS) service with Piper TTS and pyttsx3 support.

Supported engines:
- "piper": use Piper TTS (default, neural TTS, natural sounding, offline) - requires piper-tts package
- "pyttsx3": use pyttsx3 (free, offline, uses system voices) - requires pyttsx3 package
- "log": log text to console
"""

from __future__ import annotations

from typing import Optional
import logging
import tempfile
from pathlib import Path

import numpy as np

# Conditional import for sounddevice (only needed on Pi)
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    sd = None  # type: ignore
    SOUNDDEVICE_AVAILABLE = False

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Text-to-speech (TTS) service with Piper TTS and pyttsx3 support."""

    _instance: Optional["TextToSpeechService"] = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine_name = getattr(settings, "tts_engine", "log")
        self._pyttsx3 = None
        self._piper_voice = None
        self._piper_model_path = None

        # Initialize Piper TTS if requested
        if self.engine_name == "piper":
            try:
                from piper import PiperVoice  # type: ignore[import]

                # Get voice model path from settings
                voice_name = getattr(settings, "tts_voice", "") or "en_US-lessac-medium"
                model_path = getattr(settings, "tts_piper_model_path", "")
                
                # If no explicit model path, try to find it in default locations
                if not model_path:
                    # Check common locations
                    home = Path.home()
                    possible_paths = [
                        home / ".local" / "share" / "piper" / "voices" / f"{voice_name}.onnx",
                        home / ".local" / "share" / "piper" / "voices" / voice_name / f"{voice_name}.onnx",
                        Path("/usr/share/piper/voices") / f"{voice_name}.onnx",
                        # Also check for models downloaded via piper-tts package
                        Path.home() / ".cache" / "piper" / "voices" / f"{voice_name}.onnx",
                    ]
                    
                    for path in possible_paths:
                        if path.exists():
                            model_path = str(path)
                            break
                    
                    if not model_path:
                        logger.warning(
                            f"Piper model '{voice_name}' not found in default locations.\n"
                            f"Download a voice model with:\n"
                            f"  python -m piper.download_voices {voice_name}\n"
                            f"Or set TTS_PIPER_MODEL_PATH to the full path of the .onnx file.\n"
                            f"Available voices: https://github.com/rhasspy/piper/blob/master/VOICES.md"
                        )
                        self.engine_name = "log"
                        return

                # Load the voice model
                try:
                    self._piper_voice = PiperVoice.load(model_path)
                    self._piper_model_path = model_path
                    logger.info(f"Initialized Piper TTS with model: {model_path}")
                except Exception as e:
                    logger.warning(f"Failed to load Piper model '{model_path}': {e}")
                    logger.info(
                        f"Download a voice model with:\n"
                        f"  python -m piper.download_voices {voice_name}"
                    )
                    self.engine_name = "log"
            except ImportError:
                logger.warning(
                    "piper-tts not available. Install with: poetry add piper-tts"
                )
                self.engine_name = "log"
            except Exception as exc:
                logger.warning(f"Failed to initialize Piper TTS: {exc}")
                self.engine_name = "log"

        # Initialize pyttsx3 if requested
        if self.engine_name == "pyttsx3":
            try:
                import pyttsx3  # type: ignore[import]

                self._pyttsx3 = pyttsx3.init()

                # Configure voice properties (optional, can be customized via settings)
                # Get available voices
                voices = self._pyttsx3.getProperty("voices")
                if voices:
                    # Try to use specified voice, or find best available
                    voice_name = getattr(settings, "tts_voice", "")
                    if voice_name:
                        # Try to find voice by name/ID
                        found_voice = None
                        for voice in voices:
                            if voice_name.lower() in voice.name.lower() or voice_name.lower() in voice.id.lower():
                                found_voice = voice
                                break
                        if found_voice:
                            self._pyttsx3.setProperty("voice", found_voice.id)
                            logger.info(f"Using voice: {found_voice.name} ({found_voice.id})")
                        else:
                            logger.warning(f"Voice '{voice_name}' not found, using default")
                            self._pyttsx3.setProperty("voice", voices[0].id)
                    else:
                        # Prefer female voices if available (often sound more natural)
                        # Fall back to first available
                        female_voices = [v for v in voices if "female" in v.name.lower() or "+f" in v.id.lower()]
                        if female_voices:
                            self._pyttsx3.setProperty("voice", female_voices[0].id)
                            logger.info(f"Using female voice: {female_voices[0].name}")
                        else:
                            # Try to find voices with better names (avoid default)
                            mbrola_voices = [v for v in voices if "mb" in v.name.lower() or "mbrola" in v.id.lower()]
                            if mbrola_voices:
                                self._pyttsx3.setProperty("voice", mbrola_voices[0].id)
                                logger.info(f"Using MBROLA voice: {mbrola_voices[0].name}")
                            else:
                                self._pyttsx3.setProperty("voice", voices[0].id)
                                logger.info(f"Using default voice: {voices[0].name}")

                # Set speech rate (words per minute, default ~175)
                # Slower rates often sound more natural
                rate = getattr(settings, "tts_rate", 175)
                self._pyttsx3.setProperty("rate", rate)

                # Set volume (0.0 to 1.0, default 1.0)
                volume = getattr(settings, "tts_volume", 1.0)
                self._pyttsx3.setProperty("volume", volume)

                # Set pitch if supported (some platforms/voices support this)
                pitch = getattr(settings, "tts_pitch", 50)
                try:
                    self._pyttsx3.setProperty("pitch", pitch)
                except Exception:
                    # Pitch not supported on this platform/engine
                    pass

                logger.info(
                    f"Initialized pyttsx3 TTS engine (rate={rate}, volume={volume})"
                )
            except ImportError:
                logger.warning(
                    "pyttsx3 not available. Install with: poetry add pyttsx3"
                )
                self.engine_name = "log"
            except Exception as exc:  # pragma: no cover - best-effort
                error_msg = str(exc).lower()
                if "espeak" in error_msg or "espeak-ng" in error_msg:
                    logger.warning(
                        f"Failed to initialize pyttsx3: {exc}\n"
                        "On Linux, pyttsx3 requires eSpeak. Install with:\n"
                        "  sudo apt-get install espeak espeak-data\n"
                        "Or on macOS/Windows, check system TTS settings."
                    )
                else:
                    logger.warning(f"Failed to initialize pyttsx3 TTS engine: {exc}")
                self.engine_name = "log"

    @classmethod
    def get_instance(cls) -> "TextToSpeechService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(get_settings())
        return cls._instance

    def speak(self, text: str) -> None:
        """Speak text using the configured engine (or log-only fallback)."""
        text = text.strip()
        if not text:
            return

        logger.debug(f"TTS speak called with text: {text[:100]}...")
        logger.debug(f"TTS engine: {self.engine_name}, SOUNDDEVICE_AVAILABLE: {SOUNDDEVICE_AVAILABLE}")

        if self.engine_name == "piper" and self._piper_voice is not None:
            try:
                # Generate audio with Piper
                # Create temp file and get path
                tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".wav")
                tmp_path = Path(tmp_path_str)

                # Close the file descriptor so Piper can write to it
                import os
                import wave
                os.close(tmp_fd)

                # Synthesize speech to WAV file using wave module
                with wave.open(str(tmp_path), "wb") as wav_file:
                    self._piper_voice.synthesize_wav(text, wav_file)
                
                # Load and play the audio
                try:
                    import soundfile as sf
                    audio_data, sample_rate = sf.read(str(tmp_path))
                except ImportError:
                    try:
                        # Fallback to scipy if soundfile not available
                        from scipy.io import wavfile
                        sample_rate, audio_data = wavfile.read(str(tmp_path))
                    except ImportError:
                        logger.error(
                            "Need soundfile or scipy to play Piper TTS audio. "
                            "Install with: poetry add scipy"
                        )
                        tmp_path.unlink()
                        return
                
                # Convert to mono if needed
                if len(audio_data.shape) > 1:
                    audio_data = audio_data[:, 0] if audio_data.shape[1] > 0 else audio_data.flatten()
                
                # Convert to float32 if needed (sounddevice expects float32)
                if audio_data.dtype != np.float32:
                    if audio_data.dtype == np.int16:
                        audio_data = audio_data.astype(np.float32) / 32767.0
                    else:
                        audio_data = audio_data.astype(np.float32)
                
                # Get output device from AudioService if available
                output_device = None
                try:
                    from backend.services.audio_service import AudioService
                    audio_service = AudioService.get_instance()
                    if audio_service._current_output_device is not None:
                        output_device = audio_service._current_output_device
                        logger.debug(f"Using output device {output_device} for TTS playback")
                except Exception as e:
                    logger.debug(f"Could not get output device from AudioService: {e}")
                
                # Play audio with optional device selection
                if SOUNDDEVICE_AVAILABLE and sd is not None:
                    logger.info(f"Playing TTS audio: {len(audio_data)} samples at {sample_rate}Hz, device={output_device}")
                    sd.play(audio_data, samplerate=sample_rate, device=output_device)
                    sd.wait()  # Wait until playback is finished
                    logger.info("TTS playback completed")
                else:
                    logger.error(f"sounddevice not available for audio playback (SOUNDDEVICE_AVAILABLE={SOUNDDEVICE_AVAILABLE}, sd={sd})")

                # Clean up temp file
                tmp_path.unlink()

                logger.info(f"Spoke via Piper TTS: {text[:50]}...")
            except Exception as e:
                logger.error(f"Piper TTS speak error: {e}")
                logger.info(f"TTS(fallback): {text}")
        elif self.engine_name == "pyttsx3" and self._pyttsx3 is not None:
            try:
                self._pyttsx3.say(text)
                self._pyttsx3.runAndWait()
                logger.debug(f"Spoke via pyttsx3: {text[:50]}...")
            except Exception as e:
                logger.error(f"pyttsx3 speak error: {e}")
                logger.info(f"TTS(fallback): {text}")
        else:
            logger.info("TTS(log): %s", text)


__all__ = ["TextToSpeechService"]

