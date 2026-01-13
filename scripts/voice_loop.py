#!/usr/bin/env python3
"""Voice loop for H.E.N.R.Y. - handles wake word detection, STT, conversation, and TTS.

This script implements the voice interaction loop:
1. Listens for wake word via AudioService
2. When triggered, records audio and transcribes it using STT service
3. Sends transcribed text to ConversationService (direct or via API)
4. Speaks/logs the response via TextToSpeechService

Falls back to typed input if STT is not configured or recording fails.
Can work standalone (direct service calls) or integrated (via API endpoint).
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config.settings import get_settings
from backend.services.audio_service import AudioService
from backend.services.conversation_service import ConversationService
from backend.services.stt_service import SpeechToTextService
from backend.services.tts_service import TextToSpeechService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceLoop:
    """Voice interaction loop that handles wake word → STT → conversation → TTS."""

    def __init__(self, api_base_url: Optional[str] = None) -> None:
        """Initialize voice loop with required services.
        
        Args:
            api_base_url: Optional API base URL. If provided, uses API endpoint instead of direct service calls.
                         If None, uses direct service calls (default).
        """
        self.settings = get_settings()
        self.audio_service = AudioService.get_instance()
        self.stt_service = SpeechToTextService.get_instance()
        self.tts_service = TextToSpeechService.get_instance()
        
        # API mode vs direct service mode
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL")
        self.use_api = self.api_base_url is not None
        
        if self.use_api:
            if not HAS_HTTPX:
                logger.warning("httpx not available. Install with: poetry add httpx. Falling back to direct service calls.")
                self.use_api = False
            else:
                self.http_client = httpx.Client(timeout=30.0, base_url=self.api_base_url)
                logger.info(f"Using API mode: {self.api_base_url}")
        else:
            self.conversation_service = ConversationService.get_instance()
            logger.info("Using direct service calls mode")
        
        self.running = False
        self.stop_event = threading.Event()
        self.user_id = "default"
        self._shutdown_requested = False

    def _handle_conversation(self, text: str) -> dict:
        """Handle conversation via API or direct service call.
        
        Args:
            text: User input text
            
        Returns:
            Dictionary with response and intent
        """
        if self.use_api and HAS_HTTPX:
            try:
                response = self.http_client.post(
                    "/conversation/chat",
                    json={"text": text, "user_id": self.user_id},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "response": data.get("response", "I didn't understand that."),
                    "intent": data.get("intent", "chat"),
                }
            except httpx.RequestError as e:
                logger.error(f"API request failed: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"API returned error status {e.response.status_code}: {e.response.text}")
                raise
        else:
            # Direct service call
            return self.conversation_service.handle_utterance(text=text, user_id=self.user_id)

    def wake_word_callback(self, wake_word_name: str, confidence: float) -> None:
        """Handle wake word detection callback.
        
        Args:
            wake_word_name: Name of the detected wake word model
            confidence: Confidence score (0.0 to 1.0)
        """
        if self._shutdown_requested:
            return
            
        logger.info(f"Wake word '{wake_word_name}' detected (confidence: {confidence:.2f})")
        
        try:
            user_input = self._get_user_input()
            
            if not user_input:
                logger.info("No input provided, skipping conversation")
                return
            
            # Handle the conversation
            logger.info(f"User said: {user_input}")
            
            try:
                response_data = self._handle_conversation(user_input)
                response_text = response_data.get("response", "I didn't understand that.")
                logger.info(f"Assistant response: {response_text}")
                
                # Speak the response
                self.tts_service.speak(response_text)
            except Exception as e:
                logger.error(f"Conversation handling failed: {e}", exc_info=True)
                error_msg = "I'm sorry, I encountered an error processing that."
                self.tts_service.speak(error_msg)
            
        except Exception as e:
            logger.error(f"Error in wake word callback: {e}", exc_info=True)
            self.tts_service.speak("I'm sorry, I encountered an error processing that.")

    def _record_audio(self, duration_seconds: float = 3.0, sample_rate: int = 16000) -> Optional[Tuple[bytes, int]]:
        """Record audio from the microphone.
        
        Args:
            duration_seconds: How long to record (default: 3 seconds)
            sample_rate: Sample rate in Hz (default: 16000)
        
        Returns:
            Tuple of (audio_bytes, sample_rate) or None if recording failed
        """
        if not HAS_PYAUDIO:
            logger.error("PyAudio not available. Install with: poetry add pyaudio")
            return None
        
        try:
            audio = pyaudio.PyAudio()
            chunk_size = 1024
            format_type = pyaudio.paInt16
            channels = 1
            
            # Use the same input device as AudioService if set
            device_index = self.audio_service._current_input_device
            
            try:
                stream = audio.open(
                    format=format_type,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=chunk_size,
                    input_device_index=device_index,
                )
                
                logger.info(f"Recording audio for {duration_seconds} seconds...")
                frames = []
                num_chunks = int(sample_rate / chunk_size * duration_seconds)
                
                for _ in range(num_chunks):
                    if self._shutdown_requested:
                        break
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    frames.append(data)
                
                stream.stop_stream()
                stream.close()
                audio.terminate()
                
                if self._shutdown_requested:
                    return None
                
                # Concatenate all frames into a single bytes object
                audio_bytes = b''.join(frames)
                logger.info(f"Recorded {len(audio_bytes)} bytes of audio")
                return (audio_bytes, sample_rate)
                
            except Exception as e:
                logger.error(f"Error during audio recording: {e}")
                audio.terminate()
                return None
                
        except Exception as e:
            logger.error(f"Failed to record audio: {e}")
            return None

    def _get_user_input(self) -> str:
        """Get user input via STT transcription or typed fallback.
        
        Records audio after wake word detection and transcribes it using STT service.
        Falls back to typed input if STT is not configured.
        
        Returns:
            User's input text
        """
        # Check if STT is configured and available
        if self.stt_service.engine in ("none", "dummy"):
            # STT not configured - fall back to typed input
            logger.info("STT not configured, using typed input fallback")
            try:
                user_input = input("\n[Wake word detected] What did you say? (or press Enter to skip): ").strip()
                return user_input
            except (EOFError, KeyboardInterrupt):
                return ""
        
        # STT is configured - record audio and transcribe
        audio_data = self._record_audio(duration_seconds=3.0)
        if audio_data is None:
            logger.warning("Failed to record audio, falling back to typed input")
            try:
                user_input = input("\n[Recording failed] What did you say? (or press Enter to skip): ").strip()
                return user_input
            except (EOFError, KeyboardInterrupt):
                return ""
        
        audio_bytes, sample_rate = audio_data
        
        # Transcribe using STT service
        try:
            logger.info("Transcribing audio...")
            text = self.stt_service.transcribe(audio_bytes, sample_rate)
            if text:
                logger.info(f"Transcribed: {text}")
                return text.strip()
            else:
                logger.warning("Transcription returned empty text")
                # Fall back to typed input
                try:
                    user_input = input("\n[Transcription empty] What did you say? (or press Enter to skip): ").strip()
                    return user_input
                except (EOFError, KeyboardInterrupt):
                    return ""
        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            # Fall back to typed input
            try:
                user_input = input("\n[Transcription failed] What did you say? (or press Enter to skip): ").strip()
                return user_input
            except (EOFError, KeyboardInterrupt):
                return ""

    def start(self) -> None:
        """Start the voice loop."""
        if self.running:
            logger.warning("Voice loop is already running")
            return
        
        # Check if audio is enabled
        if not self.settings.audio_enabled:
            logger.warning(
                "Audio is disabled (AUDIO_ENABLED=False). "
                "Enable audio in settings to use voice loop."
            )
            return
        
        # Check audio service health
        health = self.audio_service.health_check()
        if health.get("status") != "healthy":
            logger.error(f"Audio service not healthy: {health}")
            return
        
        # Initialize wake word detection
        logger.info("Initializing wake word detection...")
        initialized = self.audio_service.initialize_wake_word_detection()
        if not initialized:
            logger.error(
                "Failed to initialize wake word detection. "
                "Make sure you have a wake word model in the model/ directory "
                "(hey_henry.tflite or hey_henry.onnx), or use a default model."
            )
            logger.info(
                "To use a default model, call: "
                "audio_service.initialize_wake_word_detection_default('alexa') "
                "or another default model name."
            )
            return
        
        # If using API, test connection
        if self.use_api:
            try:
                response = self.http_client.get("/health", timeout=5.0)
                response.raise_for_status()
                logger.info("API connection verified")
            except Exception as e:
                logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
                logger.error("Voice loop cannot start without API connection")
                return
        
        self.running = True
        self.stop_event.clear()
        self._shutdown_requested = False
        
        logger.info("Starting voice loop...")
        logger.info(f"Listening for wake word: {self.settings.wake_word}")
        logger.info("Press Ctrl+C to stop")
        
        try:
            # Start listening (this blocks until stop_event is set)
            self.audio_service.start_listening(
                callback=self.wake_word_callback,
                stop_event=self.stop_event,
                save_audio=False,  # Set to True for debugging
            )
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in voice loop: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the voice loop."""
        if not self.running:
            return
        
        logger.info("Stopping voice loop...")
        self._shutdown_requested = True
        self.running = False
        self.stop_event.set()
        
        # Cleanup
        if self.use_api and HAS_HTTPX:
            try:
                self.http_client.close()
            except Exception:
                pass


def main() -> None:
    """Main entry point for voice loop script."""
    # Get API base URL from environment or command line
    api_base_url = os.getenv("API_BASE_URL")
    
    loop = None
    try:
        loop = VoiceLoop(api_base_url=api_base_url)
        
        # Set up signal handlers for graceful shutdown
        def handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            if loop:
                loop.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        
        loop.start()
    except KeyboardInterrupt:
        logger.info("Voice loop interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in voice loop: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
