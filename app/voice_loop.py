"""Voice interaction loop for H.E.N.R.Y. - handles wake word detection and conversation."""

from __future__ import annotations

import base64
import collections
import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config.settings import get_settings
from backend.services.audio_service import AudioService
from backend.services.stt_service import SpeechToTextService
from backend.services.tts_service import TextToSpeechService

logger = logging.getLogger(__name__)

# Constants
API_HEALTH_CHECK_INTERVAL = 2.0  # Check API every 2 seconds during startup


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

        if not self.use_api:
            # Only import ConversationService when not using API mode
            # This avoids loading heavy dependencies (neo4j, ollama) on client devices
            from backend.services.conversation_service import ConversationService
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

        Records audio after wake word detection and transcribes it using remote or local STT.
        Falls back to typed input if STT is not configured.

        Returns:
            User's input text
        """
        # Check if remote STT is configured
        use_remote_stt = (
            self.settings.stt_engine == "remote" or
            (self.settings.stt_server_url and self.settings.stt_server_url.strip())
        )

        # If neither remote nor local STT is configured, fall back to typed input
        if not use_remote_stt and self.stt_service.engine in ("none", "dummy"):
            logger.info("STT not configured, using typed input fallback")
            try:
                user_input = input("\n[Wake word detected] What did you say? (or press Enter to skip): ").strip()
                return user_input
            except (EOFError, KeyboardInterrupt):
                return ""

        # Record audio with VAD
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

        # Transcribe using remote or local STT
        try:
            logger.info("Transcribing audio...")
            # Show "Transcribing..." status
            if self.gui:
                self.gui.display_transcription("Transcribing...")

            if use_remote_stt:
                # Send audio to remote STT server
                text = self._transcribe_remote(audio_bytes, sample_rate)
            else:
                # Use local STT service
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

    def _transcribe_remote(self, audio_bytes: bytes, sample_rate: int) -> str:
        """Send audio to remote STT server for transcription.

        Args:
            audio_bytes: PCM audio data (int16 format)
            sample_rate: Sample rate in Hz

        Returns:
            Transcribed text

        Raises:
            Exception: If server request fails
        """
        if not HAS_HTTPX:
            logger.error("httpx not available for remote STT. Install with: poetry add httpx")
            return ""

        try:
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_bytes).decode()

            # Send to STT server
            stt_url = self.settings.stt_server_url.rstrip("/")
            logger.info(f"Sending audio to remote STT server: {stt_url}/stt/transcribe")

            response = httpx.post(
                f"{stt_url}/stt/transcribe",
                json={"audio_data": audio_b64, "sample_rate": sample_rate},
                timeout=30.0,
            )
            response.raise_for_status()

            result = response.json()
            text = result.get("text", "")
            logger.info(f"Remote STT transcription: {text}")
            return text

        except httpx.RequestError as e:
            logger.error(f"Remote STT request failed: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Remote STT server error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Remote STT failed: {e}")
            raise

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

