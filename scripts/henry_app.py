#!/usr/bin/env python3
"""Combined H.E.N.R.Y. application - GUI + Voice Loop in one process.

This script combines:
- Tkinter GUI for visual feedback (main thread)
- Voice loop for wake word detection and voice interaction (background thread)

Both components communicate with the backend API server (dev_server.py),
which runs separately and serves as the interface for external clients.

Usage:
    # Start API server in one terminal
    poetry run python scripts/dev_server.py

    # Start combined app in another terminal
    poetry run python scripts/henry_app.py

    # Or use the convenience script
    poetry run bash scripts/dev_run_all.sh
"""

from __future__ import annotations

import collections
import json
import logging
import math
import os
import queue
import random
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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

try:
    import webrtcvad
    HAS_WEBRTCVAD = True
except ImportError:
    HAS_WEBRTCVAD = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import tkinter as tk
    from tkinter import ttk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config.settings import get_settings
from backend.services.audio_service import AudioService
from backend.services.conversation_service import ConversationService
from backend.services.stt_service import SpeechToTextService
from backend.services.tts_service import TextToSpeechService

# Import color scheme
from scripts import colors

# Configure logging based on DEBUG environment variable
DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.info(f"Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress httpx polling logs
logging.getLogger("httpcore").setLevel(logging.WARNING)  # Suppress httpcore (httpx's underlying library)
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("openwakeword").setLevel(logging.WARNING)  # Suppress openWakeWord verbose logs
logging.getLogger("openwakeword.model").setLevel(logging.WARNING)
logging.getLogger("openwakeword.utils").setLevel(logging.WARNING)
logging.getLogger("backend.services.audio_service").setLevel(logging.WARNING)  # Suppress audio prediction logs
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)  # Suppress Neo4j schema property warnings

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
POLL_INTERVAL_SECONDS = 0.5
CONNECTION_TIMEOUT = 2.0
MAX_RETRY_DELAY = 5.0
API_HEALTH_CHECK_INTERVAL = 2.0  # Check API every 2 seconds during startup


@dataclass
class UIState:
    """UI state data class."""
    active_view: str = "idle"
    status_text: str = ""
    timer_state: Dict[str, Any] | None = None
    idea_view: Dict[str, Any] | None = None
    timer_state_received_at: float = 0.0  # Timestamp when timer state was last received


class VoiceLoop:
    """Voice interaction loop that handles wake word → STT → conversation → TTS."""

    def __init__(self, api_base_url: Optional[str] = None, gui: Optional[Any] = None) -> None:
        """Initialize voice loop with required services.
        
        Args:
            api_base_url: Optional API base URL. If provided, uses API endpoint instead of direct service calls.
                         If None, uses direct service calls (default).
            gui: Optional GUI instance for displaying transcription text.
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
        self._status_callback: Optional[callable] = None
        self._last_spoken_text: Optional[str] = None  # Track what was spoken before tools
        self.gui = gui  # GUI reference for displaying transcription

        # Wake word queue-based debouncing - prevent multiple triggers from single utterance
        # Queue stores (timestamp, wake_word_name, confidence) tuples
        self._wake_word_queue: queue.Queue = queue.Queue()
        self._wake_word_worker_thread: Optional[threading.Thread] = None
        self._wake_word_window_seconds: float = 5.0  # Discard events within 5 seconds of processing
        self._processing_wake_word = False  # Flag to track if we're currently processing
        logger.info(f"Wake word queue window: {self._wake_word_window_seconds}s")

    def set_status_callback(self, callback: callable) -> None:
        """Set callback for status updates (e.g., to update GUI)."""
        self._status_callback = callback

    def _update_status(self, status: str) -> None:
        """Update status via callback if available."""
        if self._status_callback:
            try:
                self._status_callback(status)
            except Exception as e:
                logger.debug(f"Status callback error: {e}")

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
            # Direct service call - pass TTS speak function as callback
            self._last_spoken_text = None
            
            def speak_before_tools(text: str) -> None:
                """Speak text before tool execution."""
                self._last_spoken_text = text
                self.tts_service.speak(text)
            
            return self.conversation_service.handle_utterance(
                text=text, 
                user_id=self.user_id,
                pre_tool_speak_callback=speak_before_tools
            )

    def wake_word_callback(self, wake_word_name: str, confidence: float) -> None:
        """Handle wake word detection callback - enqueues events for processing.

        Args:
            wake_word_name: Name of the detected wake word model
            confidence: Confidence score (0.0 to 1.0)
        """
        if self._shutdown_requested:
            return

        # Ignore wake word if we're already processing one
        if self._processing_wake_word:
            logger.debug(f"Wake word '{wake_word_name}' ignored - already processing a request (confidence: {confidence:.2f})")
            return

        # Also ignore if queue is getting too large (shouldn't happen, but safety check)
        queue_size = self._wake_word_queue.qsize()
        if queue_size >= 3:
            logger.warning(f"Wake word queue too large ({queue_size} items), ignoring new detection")
            return

        # Timestamp and enqueue the wake word event
        timestamp = time.time()
        self._wake_word_queue.put((timestamp, wake_word_name, confidence))
        logger.debug(f"Wake word event queued: '{wake_word_name}' (confidence: {confidence:.2f}) at {timestamp:.3f}")

    def _process_wake_word_queue(self) -> None:
        """Worker thread that processes wake word events from the queue.
        
        When processing an event, discards any queued events within the time window.
        """
        while not self._shutdown_requested:
            try:
                # Get next event from queue (blocking with timeout to allow shutdown check)
                try:
                    event_timestamp, wake_word_name, confidence = self._wake_word_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Check for shutdown sentinel
                if wake_word_name == "__SHUTDOWN__":
                    self._wake_word_queue.task_done()
                    break

                # Check if we're already processing (shouldn't happen, but safety check)
                if self._processing_wake_word:
                    logger.debug(f"Wake word event ignored (already processing): '{wake_word_name}' at {event_timestamp:.3f}")
                    self._wake_word_queue.task_done()
                    continue

                # Mark as processing
                self._processing_wake_word = True
                processing_timestamp = event_timestamp

                # Discard any events in the queue that are within the time window
                discarded_count = 0
                while not self._wake_word_queue.empty():
                    try:
                        # Peek at next item without removing it
                        next_timestamp, next_name, next_confidence = self._wake_word_queue.get_nowait()
                        time_diff = abs(next_timestamp - processing_timestamp)
                        
                        if time_diff <= self._wake_word_window_seconds:
                            # Discard this event (within window)
                            logger.debug(f"Wake word event discarded (within {time_diff:.2f}s of processing): '{next_name}' at {next_timestamp:.3f}")
                            discarded_count += 1
                            self._wake_word_queue.task_done()
                        else:
                            # Put it back (outside window, keep it for later)
                            self._wake_word_queue.put((next_timestamp, next_name, next_confidence))
                            break
                    except queue.Empty:
                        break

                if discarded_count > 0:
                    logger.info(f"Discarded {discarded_count} wake word event(s) within {self._wake_word_window_seconds}s window")

                # Process the wake word event
                try:
                    logger.info(f"Wake word '{wake_word_name}' detected (confidence: {confidence:.2f})")
                    logger.debug(f"Processing wake word event: name={wake_word_name}, confidence={confidence}, timestamp={event_timestamp:.3f}")
                    self._update_status("Wake word detected - listening...")
                    
                    user_input = self._get_user_input()
                    
                    if not user_input:
                        logger.info("No input provided, skipping conversation")
                        self._update_status("No input received")
                        continue
                    
                    # Handle the conversation
                    logger.info(f"User said: {user_input}")
                    self._update_status("Processing...")
                    
                    try:
                        response_data = self._handle_conversation(user_input)
                        response_text = response_data.get("response", "I didn't understand that.")
                        logger.info(f"Assistant response: {response_text}")
                        
                        # Clear transcription display after processing
                        if self.gui:
                            self.gui.display_transcription("")
                        
                        # Speak the response only if it wasn't already spoken before tool execution
                        if response_text != self._last_spoken_text:
                            self._update_status("Speaking...")
                            self.tts_service.speak(response_text)
                        self._update_status("Ready")
                    except Exception as e:
                        logger.error(f"Conversation handling failed: {e}", exc_info=True)
                        # Clear transcription display on error
                        if self.gui:
                            self.gui.display_transcription("")
                        error_msg = "I'm sorry, I encountered an error processing that."
                        self.tts_service.speak(error_msg)
                        self._update_status("Error occurred")
                    
                except Exception as e:
                    logger.error(f"Error processing wake word event: {e}", exc_info=True)
                    self.tts_service.speak("I'm sorry, I encountered an error processing that.")
                    self._update_status("Error occurred")
                finally:
                    # Always clear the processing flag when done
                    self._processing_wake_word = False
                    self._wake_word_queue.task_done()

            except Exception as e:
                logger.error(f"Error in wake word queue worker: {e}", exc_info=True)
                self._processing_wake_word = False

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

    def _record_audio_with_vad(
        self,
        sample_rate: int = 16000,
        max_duration: float = 30.0,
        silence_duration: float = 0.5,
        vad_aggressiveness: int = 2
    ) -> Optional[Tuple[bytes, int]]:
        """Record audio until silence detected using VAD.

        Args:
            sample_rate: Sample rate in Hz (must be 8000, 16000, 32000, or 48000)
            max_duration: Maximum recording duration in seconds (safety limit)
            silence_duration: Seconds of silence before stopping recording
            vad_aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)

        Returns:
            Tuple of (audio_bytes, sample_rate) or None if recording failed
        """
        if not HAS_PYAUDIO:
            logger.error("PyAudio not available. Install with: poetry add pyaudio")
            return None

        if not HAS_WEBRTCVAD:
            logger.warning("webrtcvad not available, falling back to fixed duration recording")
            return self._record_audio(duration_seconds=5.0, sample_rate=sample_rate)

        try:
            # Initialize VAD
            vad = webrtcvad.Vad()
            vad.set_mode(vad_aggressiveness)

            audio = pyaudio.PyAudio()
            chunk_duration_ms = 30  # webrtcvad works with 10, 20, or 30ms frames
            chunk_size = int(sample_rate * chunk_duration_ms / 1000)
            format_type = pyaudio.paInt16
            channels = 1

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

                logger.info("Recording with VAD (will stop when you finish speaking)...")

                frames = []
                speech_frames = []
                silence_chunks = int(silence_duration * 1000 / chunk_duration_ms)
                max_chunks = int(max_duration * 1000 / chunk_duration_ms)

                # Ring buffer to track recent speech activity
                ring_buffer = collections.deque(maxlen=silence_chunks)
                triggered = False  # Whether we've detected speech yet

                chunk_count = 0
                while chunk_count < max_chunks:
                    if self._shutdown_requested:
                        break

                    chunk = stream.read(chunk_size, exception_on_overflow=False)
                    frames.append(chunk)

                    # VAD detection
                    is_speech = vad.is_speech(chunk, sample_rate)

                    if not triggered:
                        # Waiting for speech to start
                        ring_buffer.append((chunk, is_speech))
                        num_voiced = len([f for f, speech in ring_buffer if speech])

                        # If majority of recent frames are speech, we've started
                        if num_voiced > 0.8 * ring_buffer.maxlen:
                            triggered = True
                            logger.debug("Speech detected, recording...")
                            # Add buffered audio
                            for buffered_chunk, _ in ring_buffer:
                                speech_frames.append(buffered_chunk)
                            ring_buffer.clear()
                    else:
                        # Currently recording speech
                        # Add chunk first, then check for silence
                        speech_frames.append(chunk)
                        ring_buffer.append((chunk, is_speech))
                        num_unvoiced = len([f for f, speech in ring_buffer if not speech])

                        # If majority of recent frames are silence, we're done
                        # Use 0.7 threshold (70%) for more responsive detection
                        if num_unvoiced > 0.7 * ring_buffer.maxlen:
                            duration = chunk_count * chunk_duration_ms / 1000
                            logger.info(f"Silence detected, stopping recording (duration: {duration:.1f}s)")
                            
                            # Trim additional silence from the end - remove frames that are likely silence
                            # Remove up to silence_chunks worth of frames from the end
                            frames_to_trim = min(silence_chunks // 2, len(speech_frames))  # Trim half the silence period
                            if frames_to_trim > 0:
                                speech_frames = speech_frames[:-frames_to_trim]
                                logger.debug(f"Trimmed {frames_to_trim} silence frames from end")
                            
                            break

                    chunk_count += 1

                stream.stop_stream()
                stream.close()
                audio.terminate()

                if self._shutdown_requested or not speech_frames:
                    logger.warning("No speech detected or shutdown requested")
                    return None

                # Concatenate frames
                audio_bytes = b''.join(speech_frames)
                logger.info(f"Recorded {len(audio_bytes)} bytes with VAD")
                return (audio_bytes, sample_rate)

            except Exception as e:
                logger.error(f"Error during VAD recording: {e}", exc_info=True)
                audio.terminate()
                return None

        except Exception as e:
            logger.error(f"Failed to initialize VAD: {e}", exc_info=True)
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
        
        # STT is configured - record audio with VAD and transcribe
        audio_data = self._record_audio_with_vad(
            sample_rate=16000,
            max_duration=30.0,
            silence_duration=0.8,  # Reduced from 1.5s to 0.8s for faster response
            vad_aggressiveness=2
        )
        if audio_data is None:
            logger.warning("Failed to record audio with VAD")
            # Clear transcription display
            if self.gui:
                self.gui.display_transcription("")
            return ""
        
        audio_bytes, sample_rate = audio_data
        
        # Transcribe using STT service
        try:
            logger.info("Transcribing audio...")
            # Show "Transcribing..." status
            if self.gui:
                self.gui.display_transcription("Transcribing...")
            
            text = self.stt_service.transcribe(audio_bytes, sample_rate)
            if text:
                logger.info(f"Transcribed: {text}")
                # Display transcribed text on GUI immediately
                if self.gui:
                    self.gui.display_transcription(text.strip())
                return text.strip()
            else:
                logger.warning("Transcription returned empty text")
                # Clear transcription display
                if self.gui:
                    self.gui.display_transcription("")
                return ""
        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            # Clear transcription display on error
            if self.gui:
                self.gui.display_transcription("")
            return ""

    def _wait_for_api(self) -> bool:
        """Wait for API server to be ready.
        
        Returns:
            True if API is ready, False if timeout or error
        """
        if not self.use_api or not HAS_HTTPX:
            return True  # Not using API or httpx not available
        
        logger.info(f"Waiting for API server at {self.api_base_url}...")
        max_attempts = 30  # Wait up to 60 seconds (30 * 2s)
        attempt = 0
        
        while attempt < max_attempts and not self._shutdown_requested:
            try:
                response = self.http_client.get("/health", timeout=2.0)
                response.raise_for_status()
                logger.info("API server is ready")
                return True
            except Exception:
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(API_HEALTH_CHECK_INTERVAL)
        
        if self._shutdown_requested:
            return False
        
        logger.error(f"API server at {self.api_base_url} not ready after {max_attempts * API_HEALTH_CHECK_INTERVAL} seconds")
        return False

    def start(self) -> None:
        """Start the voice loop (should be called in a background thread)."""
        if self.running:
            logger.warning("Voice loop is already running")
            return
        
        # Check if audio is enabled
        if not self.settings.audio_enabled:
            logger.warning(
                "Audio is disabled (AUDIO_ENABLED=False). "
                "Enable audio in settings to use voice loop."
            )
            self._update_status("Audio disabled")
            return
        
        # Wait for API if using API mode
        if self.use_api:
            if not self._wait_for_api():
                self._update_status("API server not available")
                return
        
        # Check audio service health
        health = self.audio_service.health_check()
        if health.get("status") != "healthy":
            logger.error(f"Audio service not healthy: {health}")
            self._update_status("Audio service unhealthy")
            return
        
        # Initialize wake word detection
        logger.info("Initializing wake word detection...")
        self._update_status("Initializing wake word detection...")
        initialized = self.audio_service.initialize_wake_word_detection()
        if not initialized:
            logger.error(
                "Failed to initialize wake word detection. "
                "Make sure you have a wake word model in the model/ directory "
                "(hey_henry.tflite or hey_henry.onnx), or use a default model."
            )
            self._update_status("Wake word detection failed")
            return
        
        self.running = True
        self.stop_event.clear()
        self._shutdown_requested = False
        
        # Start the wake word queue worker thread
        self._wake_word_worker_thread = threading.Thread(
            target=self._process_wake_word_queue,
            daemon=True,
            name="WakeWordQueueWorker"
        )
        self._wake_word_worker_thread.start()
        logger.info("Started wake word queue worker thread")
        
        logger.info("Starting voice loop...")
        logger.info(f"Listening for wake word: {self.settings.wake_word}")
        self._update_status(f"Listening for '{self.settings.wake_word}'...")
        
        try:
            # Start listening (this blocks until stop_event is set)
            self.audio_service.start_listening(
                callback=self.wake_word_callback,
                stop_event=self.stop_event,
                save_audio=False,  # Set to True for debugging
            )
        except Exception as e:
            logger.error(f"Error in voice loop: {e}", exc_info=True)
            self._update_status("Voice loop error")
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
        self._update_status("Voice loop stopped")
        
        # Wait for wake word queue worker thread to finish
        if self._wake_word_worker_thread and self._wake_word_worker_thread.is_alive():
            logger.info("Waiting for wake word queue worker thread to finish...")
            # Put a sentinel value to wake up the worker if it's blocking
            try:
                self._wake_word_queue.put((time.time(), "__SHUTDOWN__", 0.0), timeout=1.0)
            except queue.Full:
                pass
            self._wake_word_worker_thread.join(timeout=5.0)
            if self._wake_word_worker_thread.is_alive():
                logger.warning("Wake word queue worker thread did not finish within timeout")
        
        # Drain any remaining items from the queue
        drained_count = 0
        while not self._wake_word_queue.empty():
            try:
                self._wake_word_queue.get_nowait()
                drained_count += 1
            except queue.Empty:
                break
        if drained_count > 0:
            logger.debug(f"Drained {drained_count} remaining wake word event(s) from queue")
        
        # Cleanup
        if self.use_api and HAS_HTTPX:
            try:
                self.http_client.close()
            except Exception:
                pass


class SmileyFace:
    """Animated smiley face widget - just eyes and mouth."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize smiley face.

        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Center y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.center_x = x
        self.center_y = y
        self.screen_width = screen_width
        # Use 40% of screen width for more reasonable, centered size
        self.size = int(screen_width * 0.4)
        self.base_radius = self.size // 2
        self.sleepiness_level = 0  # 0=happy, 1=neutral, 2=sleepy, 3=very sleepy
        self.animation_phase = 0.0
        self.vertical_offset = 0.0
        self.horizontal_offset = 0.0  # For personality - slight head tilts
        self.is_blinking = False
        self.blink_start_time = 0.0
        self.last_blink_time = time.time()
        self.blink_interval = 2.5 + (random.random() * 3.0)  # 2.5-5.5 seconds (more varied)
        self.is_listening = False  # Visual indicator when recording audio

        # Colors
        self.eye_color = colors.FACE_EYE_COLOR
        self.mouth_color = colors.FACE_MOUTH_COLOR

        logger.debug(f"SmileyFace initialized: center=({x}, {y}), size={self.size}, screen_width={screen_width}")

        # Draw initial face
        self._draw_face()
    
    def _draw_face(self) -> None:
        """Draw the smiley face (eyes and mouth only)."""
        # Clear previous drawing
        if hasattr(self, 'face_items') and self.face_items:
            for item in self.face_items:
                self.canvas.delete(item)
        self.face_items = []
        
        # Calculate current position with animation offsets (for personality)
        current_x = self.center_x + self.horizontal_offset
        current_y = self.center_y + self.vertical_offset
        
        # Calculate eye properties based on sleepiness level and listening state
        # Sleepiness: 0=happy, 1=neutral, 2=sleepy, 3=very sleepy
        if self.is_listening:
            # Listening: Wide, alert eyes
            eye_size_multiplier = 0.35  # 15% larger than normal
            eye_y_offset_multiplier = -0.18  # Slightly higher
        else:
            eye_size_multiplier = [0.3, 0.25, 0.2, 0.15][self.sleepiness_level]
            eye_y_offset_multiplier = [-0.15, -0.12, -0.1, -0.08][self.sleepiness_level]
        eye_x_offset = self.base_radius * 0.4  # Wider spacing
        eye_size = self.base_radius * eye_size_multiplier
        eye_y_offset = self.base_radius * eye_y_offset_multiplier
        
        # Line width scales with screen size
        line_width = max(4, int(self.screen_width * 0.01))

        # Smooth blink: scale eye height smoothly
        blink_scale = 1.0
        if self.is_blinking:
            blink_duration = 0.15  # 150ms total blink (matches update_animation)
            elapsed = time.time() - self.blink_start_time
            if elapsed < blink_duration:
                # Triangular wave (0->1 close, 1->0 open), smoothed
                t = elapsed / blink_duration
                triangle = 1.0 - abs(2 * t - 1.0)  # 0->1->0
                # Smoothstep for softer interpolation
                triangle = triangle * triangle * (3 - 2 * triangle)
                blink_scale = 1.0 - 0.95 * triangle  # down to 5% height when closed
            else:
                self.is_blinking = False
                blink_scale = 1.0

        # Draw eyes with smooth vertical scaling during blink
        # Left eye
        left_eye = self.canvas.create_oval(
            current_x - eye_x_offset - eye_size,
            current_y + eye_y_offset - (eye_size * blink_scale),
            current_x - eye_x_offset + eye_size,
            current_y + eye_y_offset + (eye_size * blink_scale),
            fill=self.eye_color,
            outline=""
        )
        self.face_items.append(left_eye)

        # Right eye
        right_eye = self.canvas.create_oval(
            current_x + eye_x_offset - eye_size,
            current_y + eye_y_offset - (eye_size * blink_scale),
            current_x + eye_x_offset + eye_size,
            current_y + eye_y_offset + (eye_size * blink_scale),
            fill=self.eye_color,
            outline=""
        )
        self.face_items.append(right_eye)
        
        # Draw droopy eyes if sleepy (level 2 or 3) - but not if blinking
        if self.sleepiness_level >= 2 and not self.is_blinking:
            # Draw semi-closed eyes (lines)
            droop_y = current_y + eye_y_offset + eye_size * 0.3
            droop_width = eye_size * 1.2
            left_droop = self.canvas.create_line(
                current_x - eye_x_offset - droop_width * 0.5,
                droop_y,
                current_x - eye_x_offset + droop_width * 0.5,
                droop_y,
                fill=self.eye_color,
                width=line_width
            )
            self.face_items.append(left_droop)

            right_droop = self.canvas.create_line(
                current_x + eye_x_offset - droop_width * 0.5,
                droop_y,
                current_x + eye_x_offset + droop_width * 0.5,
                droop_y,
                fill=self.eye_color,
                width=line_width
            )
            self.face_items.append(right_droop)
        
        # Draw mouth - adjust based on sleepiness
        mouth_y = current_y + self.base_radius * 0.25
        mouth_width = self.base_radius * 0.7  # Wider mouth
        mouth_height = self.base_radius * 0.3  # Taller mouth

        if self.sleepiness_level >= 3:
            # Very sleepy: neutral/frown mouth (straight line)
            mouth = self.canvas.create_line(
                current_x - mouth_width,
                mouth_y,
                current_x + mouth_width,
                mouth_y,
                fill=self.mouth_color,
                width=line_width
            )
        elif self.sleepiness_level == 2:
            # Sleepy: small smile (smaller arc)
            mouth = self.canvas.create_arc(
                current_x - mouth_width * 0.7,
                mouth_y - mouth_height * 0.3,
                current_x + mouth_width * 0.7,
                mouth_y + mouth_height * 0.3,
                start=180,
                extent=180,
                style="arc",
                outline=self.mouth_color,
                width=line_width
            )
        elif self.sleepiness_level == 1:
            # Neutral: normal smile
            mouth = self.canvas.create_arc(
                current_x - mouth_width * 0.85,
                mouth_y - mouth_height * 0.4,
                current_x + mouth_width * 0.85,
                mouth_y + mouth_height * 0.4,
                start=180,
                extent=180,
                style="arc",
                outline=self.mouth_color,
                width=line_width
            )
        else:
            # Happy: big smile
            mouth = self.canvas.create_arc(
                current_x - mouth_width,
                mouth_y - mouth_height * 0.5,
                current_x + mouth_width,
                mouth_y + mouth_height * 0.5,
                start=180,
                extent=180,
                style="arc",
                outline=self.mouth_color,
                width=line_width
            )
        self.face_items.append(mouth)
    
    def update_animation(self, phase: float, sleepiness_level: int = 0) -> None:
        """Update animation state.
        
        Args:
            phase: Animation phase (0.0 to 2*pi)
            sleepiness_level: Sleepiness level (0=happy, 1=neutral, 2=sleepy, 3=very sleepy)
        """
        needs_redraw = self.sleepiness_level != sleepiness_level
        if needs_redraw:
            logger.debug(f"Sleepiness level changed: {self.sleepiness_level} -> {sleepiness_level}")
        self.sleepiness_level = sleepiness_level
        self.animation_phase = phase
        
        # Check if it's time to blink
        current_time = time.time()
        if not self.is_blinking and (current_time - self.last_blink_time) >= self.blink_interval:
            self.is_blinking = True
            self.blink_start_time = current_time
            self.last_blink_time = current_time
            # Schedule next blink (random interval)
            self.blink_interval = 3.0 + (random.random() * 2.0)  # 3-5 seconds
        
        # Update blinking state
        if self.is_blinking:
            blink_duration = 0.15  # 150ms total blink
            if (current_time - self.blink_start_time) >= blink_duration:
                self.is_blinking = False
            # Force redraw during blink for smooth animation
            needs_redraw = True
        
        # Calculate vertical offset (sine wave for floating)
        # Amplitude decreases with sleepiness
        vertical_amplitudes = [10.0, 7.0, 4.0, 2.0]  # Happy, neutral, sleepy, very sleepy
        vertical_amplitude = vertical_amplitudes[min(sleepiness_level, 3)]
        new_vertical_offset = math.sin(phase) * vertical_amplitude

        # Calculate horizontal offset (slower sine wave for personality - subtle head sway)
        # Use a different phase for more natural movement
        horizontal_amplitudes = [5.0, 3.0, 2.0, 1.0]  # Happy is more animated
        horizontal_amplitude = horizontal_amplitudes[min(sleepiness_level, 3)]
        new_horizontal_offset = math.sin(phase * 0.7) * horizontal_amplitude  # 0.7x slower

        # Always redraw for smooth animation (optimized to only clear/redraw when needed)
        old_vertical_offset = self.vertical_offset
        old_horizontal_offset = self.horizontal_offset
        self.vertical_offset = new_vertical_offset
        self.horizontal_offset = new_horizontal_offset
        
        # Redraw if sleepiness level changed, blinking (eyes need to change shape), or no items yet
        if needs_redraw or self.is_blinking or not hasattr(self, 'face_items') or len(self.face_items) == 0:
            self._draw_face()
        else:
            # Move existing items for smoother animation when not blinking
            vertical_delta = new_vertical_offset - old_vertical_offset
            horizontal_delta = new_horizontal_offset - old_horizontal_offset
            # Only move if change is significant
            if abs(vertical_delta) > 0.1 or abs(horizontal_delta) > 0.1:
                for item in self.face_items:
                    self.canvas.move(item, horizontal_delta, vertical_delta)

    def set_listening(self, is_listening: bool) -> None:
        """Set listening state (shows wider/more alert eyes).

        Args:
            is_listening: Whether HENRY is currently listening/recording
        """
        if self.is_listening != is_listening:
            self.is_listening = is_listening
            logger.debug(f"Listening state changed: {is_listening}")
            self._draw_face()  # Immediately redraw with new eye size


class SevenSegmentDisplay:
    """8-segment display widget (7 segments + decimal point)."""
    
    # Segment definitions: (x1, y1, x2, y2) for each segment
    # Segments are numbered: top, upper-right, lower-right, bottom, lower-left, upper-left, middle
    # Added small gaps (0.05) to prevent rounded caps from overlapping
    SEGMENTS = [
        (0.15, 0.03, 0.85, 0.03),   # Top (0)
        (0.87, 0.08, 0.87, 0.43),   # Upper-right (1)
        (0.87, 0.57, 0.87, 0.92),   # Lower-right (2)
        (0.15, 0.97, 0.85, 0.97),   # Bottom (3)
        (0.13, 0.57, 0.13, 0.92),   # Lower-left (4)
        (0.13, 0.08, 0.13, 0.43),   # Upper-left (5)
        (0.15, 0.5, 0.85, 0.5),     # Middle (6)
    ]
    
    # Digit patterns: which segments are ON for each digit 0-9
    DIGIT_PATTERNS = [
        [0, 1, 2, 3, 4, 5],      # 0
        [1, 2],                   # 1
        [0, 1, 3, 4, 6],         # 2
        [0, 1, 2, 3, 6],         # 3
        [1, 2, 5, 6],            # 4
        [0, 2, 3, 5, 6],         # 5
        [0, 2, 3, 4, 5, 6],      # 6
        [0, 1, 2],               # 7
        [0, 1, 2, 3, 4, 5, 6],   # 8
        [0, 1, 2, 3, 5, 6],      # 9
    ]
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize 7-segment display.
        
        Args:
            canvas: Canvas to draw on
            x: Top-left x coordinate
            y: Top-left y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.x = x
        self.y = y
        self.screen_width = screen_width
        # Use 12% of screen width per digit (larger to fill screen)
        self.width = int(screen_width * 0.12)
        # Height is 1.67x width (standard 7-segment aspect ratio)
        self.height = int(self.width * 1.67)
        self.segment_items = []
        self.on_color = colors.TIMER_DIGIT_ON  # Light grey for active segments
        self.off_color = colors.TIMER_DIGIT_OFF  # Dark grey for inactive segments
        self.segment_width = max(6, int(self.width * 0.10))  # Thicker lines for better visibility
    
    def _get_segment_coords(self, segment_idx: int) -> Tuple[int, int, int, int]:
        """Get absolute coordinates for a segment.
        
        Args:
            segment_idx: Segment index (0-6)
            
        Returns:
            (x1, y1, x2, y2) coordinates
        """
        seg = self.SEGMENTS[segment_idx]
        x1 = self.x + int(seg[0] * self.width)
        y1 = self.y + int(seg[1] * self.height)
        x2 = self.x + int(seg[2] * self.width)
        y2 = self.y + int(seg[3] * self.height)
        return (x1, y1, x2, y2)
    
    def _draw_segment(self, segment_idx: int, on: bool) -> None:
        """Draw a single segment.
        
        Args:
            segment_idx: Segment index (0-6)
            on: Whether segment should be ON
        """
        x1, y1, x2, y2 = self._get_segment_coords(segment_idx)
        color = self.on_color if on else self.off_color
        
        # Draw segment as a line
        item = self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=self.segment_width,
            capstyle="round",
            joinstyle="round"
        )
        self.segment_items.append(item)
    
    def display_digit(self, digit: int) -> None:
        """Display a single digit (0-9).
        
        Args:
            digit: Digit to display (0-9)
        """
        # Clear previous display
        for item in self.segment_items:
            self.canvas.delete(item)
        self.segment_items = []
        
        if 0 <= digit <= 9:
            pattern = self.DIGIT_PATTERNS[digit]
            for seg_idx in range(7):
                self._draw_segment(seg_idx, seg_idx in pattern)
    
    def clear(self) -> None:
        """Clear the display."""
        for item in self.segment_items:
            self.canvas.delete(item)
        self.segment_items = []


class TimerDisplay:
    """Pomodoro timer display with 8-segment displays."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize timer display.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.center_x = x
        self.start_y = y
        self.screen_width = screen_width
        # Use 12% of screen width per digit (larger to fill screen)
        self.digit_width = int(screen_width * 0.12)
        self.digit_height = int(self.digit_width * 1.67)
        self.digit_spacing = int(screen_width * 0.015)  # 1.5% spacing
        self.colon_width = int(screen_width * 0.03)  # 3% for colon
        
        # Calculate total width of MM:SS display (4 digits + colon + spacing)
        # Format: MM:SS = [M][M]:[S][S]
        total_display_width = (self.digit_width * 4) + self.colon_width + (self.digit_spacing * 3)
        
        # Create displays for work timer (MM:SS) - properly centered
        work_y = y
        self.work_displays = []
        start_x = x - (total_display_width // 2)  # Start from left edge of display
        for i in range(4):  # MM:SS = 4 digits
            if i < 2:
                # Minutes digits (before colon)
                digit_x = start_x + i * (self.digit_width + self.digit_spacing)
            else:
                # Seconds digits (after colon)
                digit_x = start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing)
            display = SevenSegmentDisplay(canvas, int(digit_x), work_y, screen_width)
            self.work_displays.append(display)
        
        # Colon between minutes and seconds - properly centered
        colon_y = work_y + self.digit_height // 2
        colon_x = start_x + (self.digit_width * 2) + self.digit_spacing + (self.colon_width // 2)
        self.colon_items = []
        
        # Create displays for break timer (MM:SS) - positioned below work timer
        break_y = y + self.digit_height + int(screen_width * 0.05)  # 5% spacing
        self.break_displays = []
        for i in range(4):
            if i < 2:
                # Minutes digits (before colon)
                digit_x = start_x + i * (self.digit_width + self.digit_spacing)
            else:
                # Seconds digits (after colon)
                digit_x = start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing)
            display = SevenSegmentDisplay(canvas, int(digit_x), break_y, screen_width)
            self.break_displays.append(display)
        
        self.break_colon_items = []
    
    def _draw_colon(self, x: int, y: int, items_list: list) -> None:
        """Draw colon separator.
        
        Args:
            x: Center x coordinate
            y: Center y coordinate
            items_list: List to store colon items
        """
        # Clear previous colon
        for item in items_list:
            self.canvas.delete(item)
        items_list.clear()
        
        # Scale dot size and spacing based on screen width
        dot_size = max(6, int(self.screen_width * 0.01))
        dot_spacing = max(15, int(self.screen_width * 0.025))
        
        # Top dot
        top_dot = self.canvas.create_oval(
            x - dot_size, y - dot_spacing - dot_size,
            x + dot_size, y - dot_spacing + dot_size,
            fill=colors.TIMER_COLON_COLOR,
            outline=""
        )
        items_list.append(top_dot)
        
        # Bottom dot
        bottom_dot = self.canvas.create_oval(
            x - dot_size, y + dot_spacing - dot_size,
            x + dot_size, y + dot_spacing + dot_size,
            fill=colors.TIMER_COLON_COLOR,
            outline=""
        )
        items_list.append(bottom_dot)
    
    def update_timer(self, work_minutes: int, work_seconds: int, 
                     break_minutes: Optional[int] = None, break_seconds: Optional[int] = None) -> None:
        """Update timer display.
        
        Args:
            work_minutes: Work minutes remaining
            work_seconds: Work seconds remaining
            break_minutes: Break minutes (optional)
            break_seconds: Break seconds (optional)
        """
        # Calculate total width of MM:SS display for proper centering
        total_display_width = (self.digit_width * 4) + self.colon_width + (self.digit_spacing * 3)
        start_x = self.center_x - (total_display_width // 2)
        
        # Update work timer (MM:SS)
        work_mm_tens = work_minutes // 10
        work_mm_ones = work_minutes % 10
        work_ss_tens = work_seconds // 10
        work_ss_ones = work_seconds % 10
        
        # Update work digit positions and redraw
        for i, display in enumerate(self.work_displays):
            if i < 2:
                # Minutes digits (before colon)
                display.x = int(start_x + i * (self.digit_width + self.digit_spacing))
            else:
                # Seconds digits (after colon)
                display.x = int(start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing))
            # Update digit display
            if i == 0:
                display.display_digit(work_mm_tens)
            elif i == 1:
                display.display_digit(work_mm_ones)
            elif i == 2:
                display.display_digit(work_ss_tens)
            else:
                display.display_digit(work_ss_ones)
        
        # Draw colon for work timer - properly centered
        colon_x = start_x + (self.digit_width * 2) + self.digit_spacing + (self.colon_width // 2)
        colon_y = self.start_y + self.digit_height // 2
        self._draw_colon(colon_x, colon_y, self.colon_items)
        
        # Update break timer if provided
        if break_minutes is not None and break_seconds is not None:
            break_mm_tens = break_minutes // 10
            break_mm_ones = break_minutes % 10
            break_ss_tens = break_seconds // 10
            break_ss_ones = break_seconds % 10
            
            # Update break digit positions and redraw
            break_y = self.start_y + self.digit_height + int(self.screen_width * 0.05)
            for i, display in enumerate(self.break_displays):
                if i < 2:
                    # Minutes digits (before colon)
                    display.x = int(start_x + i * (self.digit_width + self.digit_spacing))
                else:
                    # Seconds digits (after colon)
                    display.x = int(start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing))
                display.y = break_y
                # Update digit display
                if i == 0:
                    display.display_digit(break_mm_tens)
                elif i == 1:
                    display.display_digit(break_mm_ones)
                elif i == 2:
                    display.display_digit(break_ss_tens)
                else:
                    display.display_digit(break_ss_ones)
            
            # Draw colon for break timer
            break_colon_y = break_y + self.digit_height // 2
            self._draw_colon(colon_x, break_colon_y, self.break_colon_items)
    
    def clear(self) -> None:
        """Clear the timer display."""
        for display in self.work_displays + self.break_displays:
            display.clear()
        for item in self.colon_items + self.break_colon_items:
            self.canvas.delete(item)
        self.colon_items.clear()
        self.break_colon_items.clear()


class TimerControls:
    """Touch-friendly controls for timer (pause/play and end buttons)."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int, 
                 on_pause_play: callable, on_end: callable):
        """Initialize timer controls.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for responsive sizing
            on_pause_play: Callback for pause/play button click
            on_end: Callback for end button click
        """
        self.canvas = canvas
        self.center_x = x
        self.top_y = y
        self.screen_width = screen_width
        self.on_pause_play = on_pause_play
        self.on_end = on_end
        self.items = []
        self.pause_play_rect = None
        self.end_rect = None
        self.is_paused = False
        
        # Button sizing - touch-friendly
        self.button_height = max(60, int(screen_width * 0.08))  # 8% of width, min 60px
        self.button_width = int(screen_width * 0.15)  # 15% of width
        self.button_spacing = int(screen_width * 0.03)  # 3% spacing
        
        self._draw()
    
    def _draw(self) -> None:
        """Draw the control buttons."""
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        
        # Calculate button positions (centered horizontally)
        total_width = (self.button_width * 2) + self.button_spacing
        start_x = self.center_x - (total_width // 2)
        
        # Pause/Play button (left)
        pause_play_x1 = start_x
        pause_play_y1 = self.top_y
        pause_play_x2 = start_x + self.button_width
        pause_play_y2 = self.top_y + self.button_height

        self.pause_play_rect = (pause_play_x1, pause_play_y1, pause_play_x2, pause_play_y2)

        # Draw button shadow for depth
        shadow_offset = 3
        pause_play_shadow = self.canvas.create_rectangle(
            pause_play_x1 + shadow_offset, pause_play_y1 + shadow_offset,
            pause_play_x2 + shadow_offset, pause_play_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(pause_play_shadow)

        # Draw button background
        bg_color = colors.BUTTON_PAUSE if not self.is_paused else colors.BUTTON_PLAY
        pause_play_bg = self.canvas.create_rectangle(
            pause_play_x1, pause_play_y1, pause_play_x2, pause_play_y2,
            fill=bg_color,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(pause_play_bg)

        # Draw pause/play icon (simple text for now)
        icon_text = "⏸" if not self.is_paused else "▶"
        font_size = max(20, int(self.screen_width * 0.03))
        pause_play_text = self.canvas.create_text(
            (pause_play_x1 + pause_play_x2) // 2,
            (pause_play_y1 + pause_play_y2) // 2,
            text=icon_text,
            font=("Arial", font_size, "bold"),
            fill="white"
        )
        self.items.append(pause_play_text)
        
        # End button (right)
        end_x1 = start_x + self.button_width + self.button_spacing
        end_y1 = self.top_y
        end_x2 = end_x1 + self.button_width
        end_y2 = self.top_y + self.button_height

        self.end_rect = (end_x1, end_y1, end_x2, end_y2)

        # Draw button shadow for depth
        end_shadow = self.canvas.create_rectangle(
            end_x1 + shadow_offset, end_y1 + shadow_offset,
            end_x2 + shadow_offset, end_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(end_shadow)

        # Draw button background
        end_bg = self.canvas.create_rectangle(
            end_x1, end_y1, end_x2, end_y2,
            fill=colors.BUTTON_END,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(end_bg)

        # Draw end icon/text
        end_text = self.canvas.create_text(
            (end_x1 + end_x2) // 2,
            (end_y1 + end_y2) // 2,
            text="End",
            font=("Arial", max(16, int(self.screen_width * 0.025)), "bold"),
            fill="white"
        )
        self.items.append(end_text)
    
    def handle_click(self, x: int, y: int) -> bool:
        """Handle click event. Returns True if click was handled."""
        if not self.pause_play_rect or not self.end_rect:
            return False
        
        px1, py1, px2, py2 = self.pause_play_rect
        ex1, ey1, ex2, ey2 = self.end_rect
        
        if px1 <= x <= px2 and py1 <= y <= py2:
            # Pause/Play button clicked
            self.on_pause_play()
            return True
        elif ex1 <= x <= ex2 and ey1 <= y <= ey2:
            # End button clicked
            self.on_end()
            return True
        
        return False
    
    def set_paused(self, is_paused: bool) -> None:
        """Update paused state and redraw."""
        if self.is_paused != is_paused:
            self.is_paused = is_paused
            self._draw()
    
    def clear(self) -> None:
        """Clear the controls."""
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self.pause_play_rect = None
        self.end_rect = None


class ConfirmationDialog:
    """Modal-style confirmation dialog for ending timer session."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int,
                 on_confirm: callable, on_cancel: callable):
        """Initialize confirmation dialog.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Center y coordinate
            screen_width: Screen width for responsive sizing
            on_confirm: Callback for confirm button
            on_cancel: Callback for cancel button
        """
        self.canvas = canvas
        self.center_x = x
        self.center_y = y
        self.screen_width = screen_width
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.items = []
        self.confirm_rect = None
        self.cancel_rect = None
        
        # Dialog sizing
        self.width = int(screen_width * 0.4)  # 40% of width
        self.height = int(screen_width * 0.15)  # 15% of width
        self.button_height = max(50, int(screen_width * 0.06))
        self.button_width = int(self.width * 0.35)
        
        self._draw()
    
    def _draw(self) -> None:
        """Draw the confirmation dialog."""
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        
        # Dialog background (semi-transparent overlay effect)
        x1 = self.center_x - (self.width // 2)
        y1 = self.center_y - (self.height // 2)
        x2 = self.center_x + (self.width // 2)
        y2 = self.center_y + (self.height // 2)
        
        # Background rectangle with shadow for depth
        shadow_offset = 4
        shadow = self.canvas.create_rectangle(
            x1 + shadow_offset, y1 + shadow_offset,
            x2 + shadow_offset, y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(shadow)

        bg = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=colors.DIALOG_BG,
            outline=colors.DIALOG_OUTLINE,
            width=4
        )
        self.items.append(bg)

        # Message text
        message_y = y1 + int(self.height * 0.35)
        font_size = max(16, int(self.screen_width * 0.025))
        message = self.canvas.create_text(
            self.center_x, message_y,
            text="End focus session?",
            font=("Arial", font_size, "bold"),
            fill=colors.DIALOG_TEXT
        )
        self.items.append(message)
        
        # Buttons
        button_y = y1 + int(self.height * 0.65)
        button_spacing = int(self.width * 0.1)
        total_button_width = (self.button_width * 2) + button_spacing
        button_start_x = self.center_x - (total_button_width // 2)
        
        # Cancel button (left)
        cancel_x1 = button_start_x
        cancel_y1 = button_y - (self.button_height // 2)
        cancel_x2 = cancel_x1 + self.button_width
        cancel_y2 = button_y + (self.button_height // 2)

        self.cancel_rect = (cancel_x1, cancel_y1, cancel_x2, cancel_y2)

        # Draw button shadow for depth
        shadow_offset = 3
        cancel_shadow = self.canvas.create_rectangle(
            cancel_x1 + shadow_offset, cancel_y1 + shadow_offset,
            cancel_x2 + shadow_offset, cancel_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(cancel_shadow)

        cancel_bg = self.canvas.create_rectangle(
            cancel_x1, cancel_y1, cancel_x2, cancel_y2,
            fill=colors.BUTTON_CANCEL,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(cancel_bg)

        cancel_text = self.canvas.create_text(
            (cancel_x1 + cancel_x2) // 2, button_y,
            text="Cancel",
            font=("Arial", max(14, int(self.screen_width * 0.022)), "bold"),
            fill="white"
        )
        self.items.append(cancel_text)
        
        # Confirm button (right)
        confirm_x1 = button_start_x + self.button_width + button_spacing
        confirm_y1 = cancel_y1
        confirm_x2 = confirm_x1 + self.button_width
        confirm_y2 = cancel_y2

        self.confirm_rect = (confirm_x1, confirm_y1, confirm_x2, confirm_y2)

        # Draw button shadow for depth
        confirm_shadow = self.canvas.create_rectangle(
            confirm_x1 + shadow_offset, confirm_y1 + shadow_offset,
            confirm_x2 + shadow_offset, confirm_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(confirm_shadow)

        confirm_bg = self.canvas.create_rectangle(
            confirm_x1, confirm_y1, confirm_x2, confirm_y2,
            fill=colors.BUTTON_CONFIRM,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(confirm_bg)

        confirm_text = self.canvas.create_text(
            (confirm_x1 + confirm_x2) // 2, button_y,
            text="Yes",
            font=("Arial", max(14, int(self.screen_width * 0.022)), "bold"),
            fill="white"
        )
        self.items.append(confirm_text)
    
    def handle_click(self, x: int, y: int) -> bool:
        """Handle click event. Returns True if click was handled."""
        if not self.confirm_rect or not self.cancel_rect:
            return False
        
        cx1, cy1, cx2, cy2 = self.confirm_rect
        canx1, cany1, canx2, cany2 = self.cancel_rect
        
        if cx1 <= x <= cx2 and cy1 <= y <= cy2:
            # Confirm button clicked
            self.on_confirm()
            return True
        elif canx1 <= x <= canx2 and cany1 <= y <= cany2:
            # Cancel button clicked
            self.on_cancel()
            return True
        
        return False
    
    def clear(self) -> None:
        """Clear the dialog."""
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self.confirm_rect = None
        self.cancel_rect = None


class IdeaNotification:
    """Toast-style notification for idea creation."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize idea notification.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.center_x = x
        self.top_y = y
        self.screen_width = screen_width
        # Use 37.5% of screen width for notification
        self.width = int(screen_width * 0.375)
        self.height = int(screen_width * 0.1)  # 10% of width for height
        self.items = []
        self.alpha = 0.0  # Opacity (0.0 to 1.0)
        self.visible = False
        self._fade_job: Optional[str] = None
    
    def show(self, idea_text: str) -> None:
        """Show notification with idea text.
        
        Args:
            idea_text: Text to display
        """
        self.visible = True
        self.alpha = 0.0
        self._current_text = idea_text
        self._draw(idea_text)
        self._fade_in()
    
    def _draw(self, idea_text: str) -> None:
        """Draw the notification.
        
        Args:
            idea_text: Text to display
        """
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        
        if not self.visible:
            return
        
        # Truncate text if too long (scale with screen width)
        max_chars = max(30, int(self.screen_width * 0.05))  # ~5% of width in characters
        display_text = idea_text if len(idea_text) <= max_chars else idea_text[:max_chars-3] + "..."
        
        # Calculate position
        x1 = self.center_x - self.width // 2
        y1 = self.top_y
        x2 = self.center_x + self.width // 2
        y2 = self.top_y + self.height
        
        # Background rectangle (opacity handled by fill color)
        bg_alpha = int(240 + (255 - 240) * self.alpha)  # Fade from 240 to 255
        bg_color = f"#{bg_alpha:02x}{bg_alpha:02x}{bg_alpha:02x}"
        
        bg = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=colors.NOTIFICATION_BG,
            outline=colors.NOTIFICATION_OUTLINE,
            width=2
        )
        self.items.append(bg)

        # Lightbulb icon (simple circle) - scale with screen
        icon_size = int(self.screen_width * 0.01875)  # 1.875% of width
        icon_x = x1 + icon_size
        icon_y = y1 + self.height // 2
        icon = self.canvas.create_oval(
            icon_x - icon_size, icon_y - icon_size,
            icon_x + icon_size, icon_y + icon_size,
            fill=colors.NOTIFICATION_ICON_BG,
            outline=colors.NOTIFICATION_ICON_OUTLINE,
            width=max(1, int(self.screen_width * 0.0025))
        )
        self.items.append(icon)
        
        # Text (opacity handled by fill color)
        # Fade from medium grey to light grey
        text_value = int(colors.NOTIFICATION_TEXT_START_RGB +
                        ((colors.NOTIFICATION_TEXT_END_RGB - colors.NOTIFICATION_TEXT_START_RGB) * self.alpha))
        text_color = f"#{text_value:02x}{text_value:02x}{text_value:02x}"
        
        # Scale font size based on screen width
        font_size = max(9, int(self.screen_width * 0.01375))  # ~1.375% of width
        icon_size = int(self.screen_width * 0.01875)  # 1.875% of width
        text_x = x1 + icon_size + 10
        text_y = y1 + self.height // 2
        text_item = self.canvas.create_text(
            text_x, text_y,
            text=display_text,
            fill=text_color,
            font=("Segoe UI", font_size),
            anchor="w",
            width=self.width - icon_size - 20
        )
        self.items.append(text_item)
    
    def _fade_in(self) -> None:
        """Fade in animation."""
        if not self.visible:
            return
        
        self.alpha = min(1.0, self.alpha + 0.1)
        # Redraw with new alpha (simplified - just redraw)
        if hasattr(self, '_current_text'):
            self._draw(self._current_text)
        
        if self.alpha < 1.0:
            self._fade_job = self.canvas.after(30, self._fade_in)
        else:
            # Start auto-dismiss after 5 seconds
            self.canvas.after(5000, self._fade_out)
    
    def _fade_out(self) -> None:
        """Fade out animation."""
        if not self.visible:
            return
        
        self.alpha = max(0.0, self.alpha - 0.1)
        if hasattr(self, '_current_text'):
            self._draw(self._current_text)
        
        if self.alpha > 0.0:
            self._fade_job = self.canvas.after(30, self._fade_out)
        else:
            self.visible = False
            for item in self.items:
                self.canvas.delete(item)
            self.items = []
    
    def hide(self) -> None:
        """Hide notification immediately."""
        self.visible = False
        if self._fade_job:
            self.canvas.after_cancel(self._fade_job)
        for item in self.items:
            self.canvas.delete(item)
        self.items = []


class HenryGUI(tk.Tk):
    """Tkinter GUI for H.E.N.R.Y. that polls backend API for UI state."""

    def __init__(self, voice_loop: Optional[VoiceLoop] = None, api_base_url: Optional[str] = None) -> None:
        """Initialize GUI.
        
        Args:
            voice_loop: Optional VoiceLoop instance for status display
            api_base_url: API base URL (default: from environment or module constant)
        """
        if not HAS_TKINTER:
            raise RuntimeError("tkinter not available. Install tkinter for GUI support.")
        
        super().__init__()
        self.title("H.E.N.R.Y.")
        # Get actual screen dimensions and use them
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if screen_width > 0 and screen_height > 0:
            self.geometry(f"{screen_width}x{screen_height}")
        else:
            self.geometry("800x480")
        self.configure(bg=colors.MAIN_BG)

        self._state = UIState()
        self._api_base_url = api_base_url or os.getenv("API_BASE_URL") or API_BASE_URL
        self._client = httpx.Client(timeout=CONNECTION_TIMEOUT) if HAS_HTTPX else None
        self._running = True
        self._connected = False
        self._retry_count = 0
        self._voice_loop = voice_loop

        # Load settings for personality timing
        self._settings = get_settings()
        self._happy_duration = self._settings.gui_happy_duration
        self._neutral_duration = self._settings.gui_neutral_duration
        self._sleepy_duration = self._settings.gui_sleepy_duration
        logger.info(f"GUI personality timings: Happy={self._happy_duration}s, Neutral={self._neutral_duration}s, Sleepy={self._sleepy_duration}s")
        logger.debug(f"GUI initialized: screen={screen_width}x{screen_height}, api_base_url={self._api_base_url}")

        self._build_layout()
        
        # Start polling thread
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()

    def _build_layout(self) -> None:
        """Build the GUI layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.main_frame = ttk.Frame(self, padding=0)  # No padding - fill entire window
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=colors.FRAME_BG)
        style.configure("TLabel", background=colors.FRAME_BG, foreground=colors.TEXT_PRIMARY)

        # Define custom styles for status labels
        style.configure("StatusLabel.TLabel", background=colors.FRAME_BG, foreground=colors.STATUS_CONNECTED)
        style.configure("ErrorLabel.TLabel", background=colors.FRAME_BG, foreground=colors.STATUS_DISCONNECTED)

        # Content area for smiley face, timer, etc. - fill entire frame
        self.content_canvas = tk.Canvas(
            self.main_frame,
            bg=colors.CANVAS_BG,
            highlightthickness=0
        )
        self.content_canvas.grid(row=0, column=0, sticky="nsew")
        
        # Bind to canvas resize to update layout
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Bind click events for timer controls
        self.content_canvas.bind("<Button-1>", self._on_canvas_click)
        
        # Initialize UI components
        self.smiley_face: Optional[SmileyFace] = None
        self.timer_display: Optional[TimerDisplay] = None
        self.timer_controls: Optional[TimerControls] = None
        self.confirmation_dialog: Optional[ConfirmationDialog] = None
        self.idea_notification: Optional[IdeaNotification] = None
        
        # Track last interaction time for bored state
        # Initialize to current time to ensure we start in a happy state
        self._last_interaction_time = time.time()
        self._initialization_complete = False  # Track if first UI render is done
        self._last_idea_id: Optional[str] = None
        self._animation_job: Optional[str] = None
        self._timer_update_job: Optional[str] = None
        self._last_active_view: Optional[str] = None
        self._last_status_text: str = ""
        self._last_timer_state: Dict[str, Any] = {}
        self._last_idea_view: Dict[str, Any] = {}
        self._previous_view: Optional[str] = None
        self._swipe_animation_job: Optional[str] = None
        self._swipe_items: list = []

        # Track canvas size for resize detection
        self._last_canvas_width: int = 0
        self._last_canvas_height: int = 0
        self._animation_frame_count: int = 0  # For periodic size checks
        
        # Transcription text display
        self._transcription_text: str = ""
        self._transcription_text_id: Optional[int] = None

        # Footer with connection status
        self.footer = ttk.Frame(self, padding=(16, 8))
        self.footer.grid(row=1, column=0, sticky="ew")
        self.footer.columnconfigure(0, weight=1)
        style.configure("TFrame", background=colors.FOOTER_BG)
        self.footer_label = ttk.Label(
            self.footer, 
            text=f"H.E.N.R.Y. - Connecting to {self._api_base_url}...",
            style="ErrorLabel.TLabel"
        )
        self.footer_label.grid(row=0, column=0, sticky="w")

        # Voice loop status label (if voice loop is enabled)
        if self._voice_loop:
            self.voice_status_label = ttk.Label(
                self.footer,
                text="Voice: Starting...",
                style="ErrorLabel.TLabel"
            )
            self.voice_status_label.grid(row=0, column=1, sticky="e", padx=(16, 0))

    def update_voice_status(self, status: str) -> None:
        """Update voice loop status display and listening state (thread-safe)."""
        # Update smiley face listening state based on status
        is_listening = "listening" in status.lower() and "for" not in status.lower()
        if self.smiley_face:
            try:
                self.after(0, lambda: self.smiley_face.set_listening(is_listening))
            except Exception:
                pass  # GUI might be closed

        if hasattr(self, 'voice_status_label'):
            try:
                self.after(0, lambda: self.voice_status_label.config(
                    text=f"Voice: {status}",
                    style="StatusLabel.TLabel" if status.startswith("Listening") else "ErrorLabel.TLabel"
                ))
            except Exception:
                pass  # GUI might be closed
    
    def display_transcription(self, text: str) -> None:
        """Display transcribed text on the GUI (thread-safe).
        
        Args:
            text: The transcribed text to display, or empty string to clear
        """
        def update_display():
            try:
                self._transcription_text = text
                self._draw_transcription_text()
            except Exception:
                pass  # GUI might be closed
        
        self.after(0, update_display)
    
    def _draw_transcription_text(self) -> None:
        """Draw the transcription text on the canvas."""
        # Remove existing transcription text
        if self._transcription_text_id is not None:
            try:
                self.content_canvas.delete(self._transcription_text_id)
            except Exception:
                pass
            self._transcription_text_id = None
        
        # Don't draw if text is empty
        if not self._transcription_text:
            return
        
        # Get canvas dimensions
        self.update_idletasks()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = self.winfo_width() or 800
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        # Position transcription text at bottom center, above footer
        # Use 85% from top (leaving space at bottom for footer)
        x = canvas_width // 2
        y = int(canvas_height * 0.85)
        
        # Calculate font size based on screen size (responsive)
        base_font_size = max(14, int(canvas_width * 0.02))
        font = ("Segoe UI", base_font_size)
        
        # Calculate max width for text wrapping (80% of canvas width)
        max_width = int(canvas_width * 0.8)
        
        # Draw text with word wrapping
        # Tkinter canvas text doesn't support automatic wrapping, so we'll use a simple approach
        # For longer text, we'll truncate and add ellipsis
        display_text = self._transcription_text
        if len(display_text) > 100:  # Rough character limit
            display_text = display_text[:97] + "..."
        
        try:
            self._transcription_text_id = self.content_canvas.create_text(
                x, y,
                text=display_text,
                font=font,
                fill=colors.TEXT_PRIMARY,
                anchor="center",
                width=max_width,
                justify="center"
            )
        except Exception:
            pass

    def _poll_loop(self) -> None:
        """Poll backend API in a separate thread."""
        if not HAS_HTTPX or not self._client:
            logger.warning("httpx not available, skipping API polling")
            return
        
        while self._running:
            try:
                resp = self._client.get(f"{self._api_base_url}/conversation/ui/state", timeout=CONNECTION_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()

                # Track when timer state was received for countdown calculation
                timer_state_received_at = time.time() if data.get("timer_state") else 0.0

                self._state = UIState(
                    active_view=data.get("active_view", "idle"),
                    status_text=data.get("status_text", ""),
                    timer_state=data.get("timer_state") or {},
                    idea_view=data.get("idea_view") or {},
                    timer_state_received_at=timer_state_received_at,
                )
                
                # Connection successful
                if not self._connected:
                    self._connected = True
                    self._retry_count = 0
                    logger.info(f"Connected to API server: {self._api_base_url}")
                    self.after(0, lambda: self.footer_label.config(
                        text=f"H.E.N.R.Y. - Connected to {self._api_base_url}",
                        style="StatusLabel.TLabel"
                    ))
                
                self.after(0, self._refresh_ui)
                
            except httpx.TimeoutException:
                self._handle_connection_error(f"Connection timeout - retrying...")
            except httpx.ConnectError:
                self._handle_connection_error(f"Unable to connect to {self._api_base_url} - retrying...")
            except httpx.HTTPStatusError as e:
                self._handle_connection_error(f"API error {e.response.status_code} - retrying...")
            except Exception as e:
                logger.error(f"Unexpected error in poll loop: {e}", exc_info=True)
                self._handle_connection_error(f"Unexpected error - retrying...")
            
            # Exponential backoff on retries
            if not self._connected:
                delay = min(POLL_INTERVAL_SECONDS * (2 ** min(self._retry_count, 3)), MAX_RETRY_DELAY)
                time.sleep(delay)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)

    def _handle_connection_error(self, message: str) -> None:
        """Handle connection errors with exponential backoff."""
        self._connected = False
        self._retry_count += 1
        
        def update_ui():
            self.footer_label.config(
                text=f"{message} (attempt {self._retry_count})",
                style="ErrorLabel.TLabel"
            )
        
        self.after(0, update_ui)
        logger.warning(message)

    def _refresh_ui(self) -> None:
        """Refresh UI elements with current state."""
        if not self._connected:
            return

        # On first render, ensure we start happy by resetting interaction time
        if not self._initialization_complete:
            self._last_interaction_time = time.time()
            self._initialization_complete = True

        # Check if state changed (for interaction tracking)
        view_changed = self._state.active_view != getattr(self, '_last_active_view', None)
        status_changed = self._state.status_text != getattr(self, '_last_status_text', None)
        timer_changed = self._state.timer_state != getattr(self, '_last_timer_state', None)
        idea_changed = self._state.idea_view != getattr(self, '_last_idea_view', None)

        state_changed = view_changed or status_changed or timer_changed or idea_changed

        if state_changed:
            logger.debug(f"State changed: view={view_changed}, status={status_changed}, timer={timer_changed}, idea={idea_changed}")
            if view_changed:
                logger.debug(f"View changed: {getattr(self, '_last_active_view', None)} -> {self._state.active_view}")
            self._last_interaction_time = time.time()
            self._last_active_view = self._state.active_view
            self._last_status_text = self._state.status_text
            self._last_timer_state = self._state.timer_state.copy() if self._state.timer_state else {}
            self._last_idea_view = self._state.idea_view.copy() if self._state.idea_view else {}
        
        # Get canvas dimensions - use actual window size
        self.update_idletasks()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        
        # Default to window size if canvas not yet rendered
        if canvas_width <= 1:
            canvas_width = self.winfo_width() or 800
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        # Use minimal padding (1% on all sides for maximum screen usage)
        padding = int(min(canvas_width, canvas_height) * 0.01)
        usable_width = canvas_width - (padding * 2)
        usable_height = canvas_height - (padding * 2)
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Only clear and redraw if view changed or timer needs update
        # Preserve confirmation dialog state before clearing
        had_confirmation_dialog = self.confirmation_dialog is not None
        if view_changed or (self._state.active_view == "pomodoro" and timer_changed):
            # Clear canvas only when view changes
            self.content_canvas.delete("all")
            self.smiley_face = None
            self.timer_display = None
            self.timer_controls = None
            # Clear confirmation dialog reference (will redraw if it was visible)
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
            # Only reset dialog on view change, preserve it on timer updates
            if view_changed:
                self.confirmation_dialog = None
                had_confirmation_dialog = False
            else:
                self.confirmation_dialog = None
            # Reset transcription text ID so it gets redrawn
            self._transcription_text_id = None
        
        # Calculate sleepiness level based on time since last interaction
        # Uses configured thresholds from settings
        time_since_interaction = time.time() - self._last_interaction_time
        if time_since_interaction < self._happy_duration:
            sleepiness_level = 0  # Happy
        elif time_since_interaction < self._neutral_duration:
            sleepiness_level = 1  # Neutral
        elif time_since_interaction < self._sleepy_duration:
            sleepiness_level = 2  # Sleepy
        else:
            sleepiness_level = 3  # Very sleepy (asleep)
        
        # Handle different views with swipe animation
        previous_view = getattr(self, '_previous_view', None)
        is_tool_view = self._state.active_view in ("pomodoro", "ideas")
        was_tool_view = previous_view in ("pomodoro", "ideas")
        
        # Trigger swipe animation if switching TO a tool view
        swipe_animating = False
        if view_changed and is_tool_view and not was_tool_view:
            self._animate_swipe_in(center_x, center_y, canvas_width, sleepiness_level)
            swipe_animating = True
        
        # Normal view update (runs after swipe animation starts or if no swipe needed)
        if self._state.active_view == "pomodoro" and self._state.timer_state:
            # Show timer display (unless swipe animation is handling it)
            if not swipe_animating:
                if self.timer_display is None or view_changed:
                    # Position timer at 35% from top (centered vertically in upper portion)
                    timer_y = int(canvas_height * 0.35)
                    self._show_timer_display(center_x, timer_y, canvas_width)
                else:
                    # Update timer display screen width if changed
                    if hasattr(self.timer_display, 'screen_width') and self.timer_display.screen_width != canvas_width:
                        # Recreate timer display with new screen width
                        timer_y = int(canvas_height * 0.35)
                        self.timer_display.clear()
                        self.timer_display = None
                        self._show_timer_display(center_x, timer_y, canvas_width)
                    else:
                        # Just update timer values
                        self._update_timer_display()
                
                # Show timer controls below timer display
                timer_status = self._state.timer_state.get("status", "paused")
                if self.timer_controls is None or view_changed:
                    # Position controls below timer (work timer + break timer + spacing)
                    timer_display_height = (self.timer_display.digit_height * 2) + int(canvas_width * 0.05) if self.timer_display else 200
                    controls_y = int(canvas_height * 0.35) + timer_display_height + int(canvas_width * 0.05)
                    self._show_timer_controls(center_x, controls_y, canvas_width, timer_status == "paused")
                else:
                    # Update controls state
                    self.timer_controls.set_paused(timer_status == "paused")

                # Redraw confirmation dialog if it was visible before canvas clear
                if had_confirmation_dialog and self.confirmation_dialog is None:
                    self.confirmation_dialog = ConfirmationDialog(
                        self.content_canvas, center_x, center_y, canvas_width,
                        on_confirm=self._handle_end_confirm,
                        on_cancel=self._handle_end_cancel
                    )
            # Hide smiley face
            if self.smiley_face:
                for item in getattr(self.smiley_face, 'face_items', []):
                    self.content_canvas.delete(item)
                self.smiley_face = None
            # Start timer update loop if timer is running (always check, not just if job is None)
            timer_status = self._state.timer_state.get("status", "paused")
            if timer_status == "running":
                if self._timer_update_job is None:
                    self._start_timer_update_loop()
            else:
                # Stop timer updates if not running
                if self._timer_update_job:
                    self.after_cancel(self._timer_update_job)
                    self._timer_update_job = None
        elif self._state.active_view == "ideas":
            # Show idea notification if new idea (unless swipe animation is handling it)
            if not swipe_animating:
                idea_id = self._state.idea_view.get("active_idea_id")
                if idea_id and idea_id != self._last_idea_id:
                    idea_text = self._state.idea_view.get("draft_text", "New idea captured")
                    self._show_idea_notification(center_x, padding, idea_text, canvas_width)
                    self._last_idea_id = idea_id
            # Also show smiley face in background
            if self.smiley_face is None or view_changed:
                self._show_smiley_face(center_x, center_y, canvas_width)
            # Stop timer updates
            if self._timer_update_job:
                self.after_cancel(self._timer_update_job)
                self._timer_update_job = None
        else:
            # Idle view - show smiley face
            if self.smiley_face is None or view_changed:
                self._show_smiley_face(center_x, center_y, canvas_width)
            # Hide timer
            if self.timer_display:
                self.timer_display.clear()
                self.timer_display = None
            # Hide timer controls
            if self.timer_controls:
                self.timer_controls.clear()
                self.timer_controls = None
            # Hide confirmation dialog if visible
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
                self.confirmation_dialog = None
            # Stop timer updates
            if self._timer_update_job:
                self.after_cancel(self._timer_update_job)
                self._timer_update_job = None
        
        # Update sleepiness level for smiley face
        if self.smiley_face:
            self.smiley_face.sleepiness_level = sleepiness_level
        
        # Store previous view for next comparison
        self._previous_view = self._state.active_view
        
        # Redraw transcription text if it exists (in case canvas was cleared)
        if self._transcription_text:
            self._draw_transcription_text()
        
        # Start animation loop if not already running
        if self._animation_job is None:
            self._start_animation_loop()
    
    def _start_timer_update_loop(self) -> None:
        """Start timer update loop (updates every second when running)."""
        if not self._running:
            self._timer_update_job = None
            return
        
        # Only update if timer is active and running
        if (self._state.active_view == "pomodoro" and 
            self._state.timer_state and 
            self._state.timer_state.get("status") == "running"):
            # Update timer display
            self._update_timer_display()
            # Schedule next update
            self._timer_update_job = self.after(1000, self._start_timer_update_loop)
        else:
            # Timer stopped or paused
            self._timer_update_job = None
    
    def _update_timer_display(self) -> None:
        """Update timer display values without full UI refresh."""
        if self.timer_display is None:
            return

        timer_state = self._state.timer_state
        if not timer_state:
            return

        # Get remaining seconds from state (calculated server-side)
        remaining_work_seconds = timer_state.get("remaining_work_seconds", 0)
        remaining_break_seconds = timer_state.get("remaining_break_seconds", 0)
        phase = timer_state.get("phase", "work")
        status = timer_state.get("status", "paused")

        # If timer is running, calculate elapsed time since last state update
        if status == "running" and self._state.timer_state_received_at > 0:
            elapsed_since_update = int(time.time() - self._state.timer_state_received_at)

            # Subtract elapsed time from the appropriate counter based on phase
            if phase == "work":
                remaining_work_seconds = max(0, remaining_work_seconds - elapsed_since_update)
            elif phase == "break":
                remaining_break_seconds = max(0, remaining_break_seconds - elapsed_since_update)

        work_minutes = remaining_work_seconds // 60
        work_seconds = remaining_work_seconds % 60

        # Always show both timers (work on top, break below)
        # Break timer shows remaining time if in break phase, otherwise full duration
        break_minutes = remaining_break_seconds // 60
        break_seconds = remaining_break_seconds % 60
        self.timer_display.update_timer(
            work_minutes, work_seconds,
            break_minutes=break_minutes,
            break_seconds=break_seconds
        )
    
    def _show_smiley_face(self, x: int, y: int, screen_width: int) -> None:
        """Show smiley face at position.
        
        Args:
            x: Center x coordinate
            y: Center y coordinate
            screen_width: Screen width for responsive sizing
        """
        if self.smiley_face is None:
            self.smiley_face = SmileyFace(self.content_canvas, x, y, screen_width)
        else:
            # Update position and screen width if changed
            if self.smiley_face.screen_width != screen_width:
                self.smiley_face.screen_width = screen_width
                self.smiley_face.size = int(screen_width * 0.4)
                self.smiley_face.base_radius = self.smiley_face.size // 2
            self.smiley_face.center_x = x
            self.smiley_face.center_y = y
            # Redraw if position changed significantly
            if abs(self.smiley_face.center_x - x) > 10 or abs(self.smiley_face.center_y - y) > 10:
                self.smiley_face._draw_face()
    
    def _on_canvas_click(self, event) -> None:
        """Handle canvas click events for timer controls and confirmation dialog."""
        x, y = event.x, event.y
        
        # Check confirmation dialog first (if visible)
        if self.confirmation_dialog:
            if self.confirmation_dialog.handle_click(x, y):
                return
        
        # Check timer controls (if visible)
        if self.timer_controls:
            if self.timer_controls.handle_click(x, y):
                return
    
    def _on_canvas_configure(self, event) -> None:
        """Handle canvas resize event."""
        # Only trigger UI refresh if size actually changed significantly
        new_width = event.width
        new_height = event.height

        # Check if size changed by more than a few pixels (avoid micro-adjustments)
        width_changed = abs(new_width - self._last_canvas_width) > 5
        height_changed = abs(new_height - self._last_canvas_height) > 5

        if width_changed or height_changed:
            logger.debug(f"Canvas resized: {self._last_canvas_width}x{self._last_canvas_height} -> {new_width}x{new_height}")
            self._last_canvas_width = new_width
            self._last_canvas_height = new_height

            # Trigger UI refresh to recenter and resize elements
            if self._connected:
                # Force redraw by clearing smiley face and timer
                if self.smiley_face:
                    for item in getattr(self.smiley_face, 'face_items', []):
                        self.content_canvas.delete(item)
                    self.smiley_face = None
                    logger.debug("Cleared smiley face for resize")

                if self.timer_display:
                    self.timer_display.clear()
                    self.timer_display = None
                    logger.debug("Cleared timer display for resize")
                
                if self.timer_controls:
                    self.timer_controls.clear()
                    self.timer_controls = None
                    logger.debug("Cleared timer controls for resize")

                # Refresh UI will recreate elements at new center
                self._refresh_ui()
    
    def _animate_swipe_in(self, center_x: int, center_y: int, screen_width: int, sleepiness_level: int) -> None:
        """Animate swipe-in from right when switching to tool view.
        
        Args:
            center_x: Center x coordinate
            center_y: Center y coordinate
            screen_width: Screen width
            sleepiness_level: Current sleepiness level
        """
        # Cancel any existing swipe animation
        if self._swipe_animation_job:
            self.after_cancel(self._swipe_animation_job)
        
        # Clear swipe items
        for item in self._swipe_items:
            try:
                self.content_canvas.delete(item)
            except:
                pass
        self._swipe_items = []
        
        # Create the view content off-screen to the right
        start_x = screen_width + 100  # Start off-screen right
        target_x = center_x  # Target position
        
        # Get canvas dimensions for proper positioning
        self.update_idletasks()
        canvas_height = self.content_canvas.winfo_height()
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        # Create the view based on active_view (off-screen)
        if self._state.active_view == "pomodoro" and self._state.timer_state:
            # Create timer display off-screen - use proper timer y position
            timer_y = int(canvas_height * 0.35)
            self._show_timer_display(start_x, timer_y, screen_width)
            # Collect all items for animation AFTER they're created
            if self.timer_display:
                # Force update to ensure items are created
                self._update_timer_display()
                for display in self.timer_display.work_displays + self.timer_display.break_displays:
                    self._swipe_items.extend(display.segment_items)
                self._swipe_items.extend(self.timer_display.colon_items)
                self._swipe_items.extend(self.timer_display.break_colon_items)
            
            # Also create and animate timer controls
            timer_status = self._state.timer_state.get("status", "paused")
            timer_display_height = (self.timer_display.digit_height * 2) + int(screen_width * 0.05) if self.timer_display else 200
            controls_y = int(canvas_height * 0.35) + timer_display_height + int(screen_width * 0.05)
            self._show_timer_controls(start_x, controls_y, screen_width, timer_status == "paused")
            if self.timer_controls:
                self._swipe_items.extend(self.timer_controls.items)
        elif self._state.active_view == "ideas":
            # Create idea notification off-screen
            idea_id = self._state.idea_view.get("active_idea_id")
            if idea_id:
                idea_text = self._state.idea_view.get("draft_text", "New idea captured")
                self._show_idea_notification(start_x, int(screen_width * 0.05), idea_text, screen_width)
                if self.idea_notification:
                    self._swipe_items.extend(self.idea_notification.items)
        
        # Animate swipe-in with time-based lerp for smoother animation
        animation_duration_ms = 500  # Increased duration for smoother feel (500ms)
        frame_time_ms = 8  # More frequent updates (~120 FPS target, but will adapt to actual frame rate)
        start_time = [time.time() * 1000]  # Start time in milliseconds
        last_x = [start_x]  # Last x position for delta calculation
        
        def animate_frame():
            current_time_ms = time.time() * 1000
            elapsed_ms = current_time_ms - start_time[0]
            
            if elapsed_ms >= animation_duration_ms:
                # Animation complete - ensure final position
                final_delta = target_x - last_x[0]
                if abs(final_delta) > 0.1:
                    for item in self._swipe_items:
                        try:
                            self.content_canvas.move(item, final_delta, 0)
                        except:
                            pass
                
                if self.timer_display:
                    self.timer_display.center_x = target_x
                    # Force final update
                    self._update_timer_display()
                if self.idea_notification:
                    self.idea_notification.center_x = target_x
                if self.timer_controls:
                    # Also animate controls if they exist
                    self.timer_controls.center_x = target_x
                self._swipe_animation_job = None
                return
            
            # Normalized progress (0.0 to 1.0)
            t = min(1.0, elapsed_ms / animation_duration_ms)
            
            # Smooth ease-out curve: 1 - (1-t)^3
            # This provides smooth deceleration
            ease_t = 1 - pow(1 - t, 3)
            
            # Lerp current x position
            current_x = start_x + (target_x - start_x) * ease_t
            
            # Calculate delta from last position for smooth movement
            delta_x = current_x - last_x[0]
            
            # Only move if delta is significant (reduces jitter and improves performance)
            if abs(delta_x) > 0.5:
                # Move all items smoothly
                for item in self._swipe_items:
                    try:
                        self.content_canvas.move(item, delta_x, 0)
                    except:
                        pass
                
                # Update display positions
                if self.timer_display:
                    self.timer_display.center_x = current_x
                if self.idea_notification:
                    self.idea_notification.center_x = current_x
                if self.timer_controls:
                    self.timer_controls.center_x = current_x
                
                last_x[0] = current_x
            
            # Schedule next frame - use adaptive timing
            # If we're behind, use shorter delay to catch up
            actual_frame_time = time.time() * 1000 - current_time_ms
            if actual_frame_time > frame_time_ms * 2:
                # We're running slow, use shorter delay to catch up
                next_delay = max(4, int(frame_time_ms * 0.5))
            else:
                next_delay = frame_time_ms
            
            self._swipe_animation_job = self.after(next_delay, animate_frame)
        
        # Start animation
        animate_frame()
    
    def _show_timer_display(self, x: int, y: int, screen_width: int) -> None:
        """Show timer display at position.
        
        Args:
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for responsive sizing
        """
        # Always recreate if screen width changed or doesn't exist
        if (self.timer_display is None or
            (hasattr(self.timer_display, 'screen_width') and self.timer_display.screen_width != screen_width)):
            # Clear old display
            if self.timer_display:
                self.timer_display.clear()
            self.timer_display = TimerDisplay(self.content_canvas, x, y, screen_width)
        else:
            # Update position
            self.timer_display.center_x = x
            self.timer_display.start_y = y
        
        # Update timer values after creating/positioning display
        self._update_timer_display()
    
    def _show_timer_controls(self, x: int, y: int, screen_width: int, is_paused: bool) -> None:
        """Show timer controls at position.
        
        Args:
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for responsive sizing
            is_paused: Whether timer is currently paused
        """
        if self.timer_controls is None or (
            hasattr(self.timer_controls, 'screen_width') and self.timer_controls.screen_width != screen_width
        ):
            # Clear old controls
            if self.timer_controls:
                self.timer_controls.clear()
            self.timer_controls = TimerControls(
                self.content_canvas, x, y, screen_width,
                on_pause_play=self._handle_pause_play,
                on_end=self._handle_end_click
            )
        else:
            # Update position and state
            self.timer_controls.center_x = x
            self.timer_controls.top_y = y
            self.timer_controls.set_paused(is_paused)
    
    def _handle_pause_play(self) -> None:
        """Handle pause/play button click."""
        timer_state = self._state.timer_state
        if not timer_state:
            return
        
        session_id = timer_state.get("session_id")
        if not session_id:
            return
        
        status = timer_state.get("status", "paused")
        api_url = f"{self._api_base_url}/productivity/pomodoro/{session_id}"
        
        try:
            if status == "running":
                # Pause the timer
                response = self._client.post(f"{api_url}/pause", timeout=CONNECTION_TIMEOUT)
                response.raise_for_status()
                logger.info("Timer paused")
            else:
                # Resume the timer
                response = self._client.post(f"{api_url}/resume", timeout=CONNECTION_TIMEOUT)
                response.raise_for_status()
                logger.info("Timer resumed")
            
            # Refresh UI state will update controls
            self._refresh_ui()
        except Exception as e:
            logger.error(f"Error toggling timer: {e}", exc_info=True)
    
    def _handle_end_click(self) -> None:
        """Handle end button click - show confirmation dialog."""
        # Show confirmation dialog
        self.update_idletasks()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        if canvas_width <= 1:
            canvas_width = self.winfo_width() or 800
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        if self.confirmation_dialog:
            self.confirmation_dialog.clear()
        
        self.confirmation_dialog = ConfirmationDialog(
            self.content_canvas, center_x, center_y, canvas_width,
            on_confirm=self._handle_end_confirm,
            on_cancel=self._handle_end_cancel
        )
    
    def _handle_end_confirm(self) -> None:
        """Handle confirmation to end timer session."""
        timer_state = self._state.timer_state
        if not timer_state:
            return
        
        session_id = timer_state.get("session_id")
        if not session_id:
            return
        
        api_url = f"{self._api_base_url}/productivity/pomodoro/{session_id}/stop"
        
        try:
            response = self._client.post(api_url, timeout=CONNECTION_TIMEOUT)
            response.raise_for_status()
            logger.info("Timer session ended")
            
            # Clear confirmation dialog
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
                self.confirmation_dialog = None
            
            # Reset interaction time to make Henry happy
            self._last_interaction_time = time.time()
            
            # Refresh UI - will show idle view with happy Henry
            self._refresh_ui()
        except Exception as e:
            logger.error(f"Error ending timer session: {e}", exc_info=True)
            # Clear dialog even on error
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
                self.confirmation_dialog = None
    
    def _handle_end_cancel(self) -> None:
        """Handle cancellation of end timer session."""
        if self.confirmation_dialog:
            self.confirmation_dialog.clear()
            self.confirmation_dialog = None
    
    def _show_idea_notification(self, x: int, y: int, text: str, screen_width: int) -> None:
        """Show idea notification.
        
        Args:
            x: Center x coordinate
            y: Top y coordinate
            text: Idea text
            screen_width: Screen width for responsive sizing
        """
        if self.idea_notification is None or (hasattr(self.idea_notification, 'screen_width') and self.idea_notification.screen_width != screen_width):
            self.idea_notification = IdeaNotification(self.content_canvas, x, y, screen_width)
        
        self.idea_notification._current_text = text
        self.idea_notification.show(text)
    
    def _start_animation_loop(self) -> None:
        """Start the animation loop for smiley face."""
        if not self._running:
            return

        # Periodically check canvas size (every 2 seconds = 120 frames at 60 FPS)
        self._animation_frame_count += 1
        if self._animation_frame_count % 120 == 0:
            canvas_width = self.content_canvas.winfo_width()
            canvas_height = self.content_canvas.winfo_height()

            # Check if size changed significantly (more than 5 pixels)
            if (abs(canvas_width - self._last_canvas_width) > 5 or
                abs(canvas_height - self._last_canvas_height) > 5):
                logger.debug(f"Periodic size check: canvas size changed {self._last_canvas_width}x{self._last_canvas_height} -> {canvas_width}x{canvas_height}")
                self._last_canvas_width = canvas_width
                self._last_canvas_height = canvas_height

                # Trigger recenter by clearing and forcing refresh
                if self.smiley_face:
                    for item in getattr(self.smiley_face, 'face_items', []):
                        self.content_canvas.delete(item)
                    self.smiley_face = None

                if self.timer_display:
                    self.timer_display.clear()
                    self.timer_display = None

                # Next refresh will recreate at new center
                if self._connected:
                    self._refresh_ui()

        # Calculate sleepiness level based on time since last interaction
        # Uses configured thresholds from settings
        time_since_interaction = time.time() - self._last_interaction_time
        if time_since_interaction < self._happy_duration:
            sleepiness_level = 0  # Happy
        elif time_since_interaction < self._neutral_duration:
            sleepiness_level = 1  # Neutral
        elif time_since_interaction < self._sleepy_duration:
            sleepiness_level = 2  # Sleepy
        else:
            sleepiness_level = 3  # Very sleepy (asleep)

        # Update smiley face animation if it exists
        if self.smiley_face:
            # Use current time for animation phase
            # Animation speed decreases with sleepiness
            animation_speeds = [0.6, 0.5, 0.3, 0.15]  # Happy, neutral, sleepy, very sleepy
            animation_speed = animation_speeds[min(sleepiness_level, 3)]
            phase = (time.time() * animation_speed) % (2 * math.pi)
            self.smiley_face.update_animation(phase, sleepiness_level)

        # Schedule next frame (16ms = ~60 FPS for smooth animation)
        self._animation_job = self.after(16, self._start_animation_loop)

    def on_close(self) -> None:
        """Handle window close event."""
        logger.info("Closing GUI and shutting down...")
        self._running = False
        
        # Cancel animation jobs
        if self._animation_job:
            self.after_cancel(self._animation_job)
            self._animation_job = None
        if self._timer_update_job:
            self.after_cancel(self._timer_update_job)
            self._timer_update_job = None
        if self._swipe_animation_job:
            self.after_cancel(self._swipe_animation_job)
            self._swipe_animation_job = None
        
        # Stop voice loop if it exists
        if self._voice_loop:
            self._voice_loop.stop()
        
        # Close HTTP client
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        
        # Destroy window
        self.destroy()


class HenryApp:
    """Combined H.E.N.R.Y. application with GUI and voice loop."""

    def __init__(self, enable_voice: bool = True, api_base_url: Optional[str] = None) -> None:
        """Initialize combined application.
        
        Args:
            enable_voice: Whether to enable voice loop (default: True)
            api_base_url: API base URL (default: from environment or module constant)
        """
        self.enable_voice = enable_voice
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL") or API_BASE_URL
        self.voice_loop: Optional[VoiceLoop] = None
        self.voice_thread: Optional[threading.Thread] = None
        self.gui: Optional[HenryGUI] = None
        self._shutdown_requested = False

    def start(self) -> None:
        """Start the combined application."""
        logger.info("Starting H.E.N.R.Y. combined application...")
        
        # Initialize voice loop if enabled
        if self.enable_voice:
            try:
                # Create voice loop without GUI first (will set GUI reference after GUI is created)
                self.voice_loop = VoiceLoop(api_base_url=self.api_base_url)
                logger.info("Voice loop initialized")
            except Exception as e:
                logger.error(f"Failed to initialize voice loop: {e}", exc_info=True)
                self.enable_voice = False
        
        # Initialize GUI
        try:
            if not HAS_TKINTER:
                logger.error("tkinter not available. GUI cannot be started.")
                raise RuntimeError("tkinter not available")
            
            self.gui = HenryGUI(voice_loop=self.voice_loop if self.enable_voice else None, api_base_url=self.api_base_url)
            
            # Set up status callback and GUI reference for voice loop
            if self.voice_loop:
                self.voice_loop.set_status_callback(self.gui.update_voice_status)
                self.voice_loop.gui = self.gui  # Set GUI reference for transcription display
            
            logger.info("GUI initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GUI: {e}", exc_info=True)
            raise
        
        # Start voice loop in background thread if enabled
        if self.enable_voice and self.voice_loop:
            try:
                self.voice_thread = threading.Thread(
                    target=self.voice_loop.start,
                    daemon=True,
                    name="VoiceLoop"
                )
                self.voice_thread.start()
                logger.info("Voice loop thread started")
            except Exception as e:
                logger.error(f"Failed to start voice loop thread: {e}", exc_info=True)
        
        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Set up window close handler
        self.gui.protocol("WM_DELETE_WINDOW", self.gui.on_close)
        
        # Run GUI mainloop (blocks until window is closed)
        logger.info("Starting GUI mainloop...")
        try:
            self.gui.mainloop()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        if self._shutdown_requested:
            return
        
        logger.info("Shutting down H.E.N.R.Y. application...")
        self._shutdown_requested = True
        
        # Stop voice loop
        if self.voice_loop:
            self.voice_loop.stop()
        
        # Wait for voice thread to finish
        if self.voice_thread and self.voice_thread.is_alive():
            logger.info("Waiting for voice loop thread to finish...")
            self.voice_thread.join(timeout=5.0)
            if self.voice_thread.is_alive():
                logger.warning("Voice loop thread did not finish within timeout")
        
        logger.info("Shutdown complete")


def main() -> None:
    """Main entry point for combined H.E.N.R.Y. application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="H.E.N.R.Y. Combined Application (GUI + Voice Loop)")
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable voice loop (GUI only mode)"
    )
    parser.add_argument(
        "--api-url",
        default=API_BASE_URL,
        help=f"API base URL (default: {API_BASE_URL})"
    )
    
    args = parser.parse_args()
    
    # Get API base URL (from args or environment or default)
    api_base_url = args.api_url
    if api_base_url != API_BASE_URL:
        os.environ["API_BASE_URL"] = api_base_url
    
    try:
        app = HenryApp(enable_voice=not args.no_voice, api_base_url=api_base_url)
        app.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

