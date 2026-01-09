"""Audio service with device detection and wake word detection."""

import logging
import platform
import time as time_module
from time import time, sleep
from pathlib import Path
from typing import Optional

import numpy as np
import pyaudio
import sounddevice as sd
from openwakeword import Model
import openwakeword.utils

try:
    from scipy.io import wavfile
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    try:
        import soundfile as sf
        HAS_SOUNDFILE = True
    except ImportError:
        HAS_SOUNDFILE = False

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class AudioService:
    """Audio service with wake word detection and device management."""

    _instance: Optional["AudioService"] = None
    _oww_model: Optional[Model] = None

    def __init__(self, settings: Settings):
        """Initialize audio service."""
        self.settings = settings
        self.audio_enabled = settings.audio_enabled
        self.wake_word = settings.wake_word
        self._wake_word_detected = False
        self._current_input_device: Optional[int] = None
        self._current_output_device: Optional[int] = None
        self._target_model_name: Optional[str] = None  # For filtering default models

    @classmethod
    def get_instance(cls) -> "AudioService":
        """Get or create the singleton instance."""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(settings)
        return cls._instance

    def health_check(self) -> dict:
        """
        Check audio service health.

        Returns:
            dict: Health status
        """
        if not self.audio_enabled:
            return {
                "status": "disabled",
                "enabled": False,
                "message": "Audio is disabled (local development mode)",
            }

        try:
            # Check if audio devices are available
            devices = self.list_devices()
            input_devices = [d for d in devices if d["max_input_channels"] > 0]
            output_devices = [d for d in devices if d["max_output_channels"] > 0]

            if not input_devices:
                return {
                    "status": "unhealthy",
                    "enabled": True,
                    "error": "No input devices found",
                }

            if not output_devices:
                return {
                    "status": "unhealthy",
                    "enabled": True,
                    "error": "No output devices found",
                }

            # Check wake word detection
            wake_word_status = "ready" if self._oww_model else "not_initialized"

            return {
                "status": "healthy",
                "enabled": True,
                "input_devices": len(input_devices),
                "output_devices": len(output_devices),
                "wake_word": self.wake_word,
                "wake_word_status": wake_word_status,
            }
        except Exception as e:
            logger.error(f"Audio health check failed: {e}")
            return {
                "status": "unhealthy",
                "enabled": True,
                "error": str(e),
            }

    def list_devices(self) -> list[dict]:
        """
        List available audio devices.

        Returns:
            list: List of audio device dictionaries
        """
        try:
            devices = sd.query_devices()
            device_list = []
            for i, device in enumerate(devices):
                # Calculate total channels (input + output)
                total_channels = device["max_input_channels"] + device["max_output_channels"]
                device_list.append(
                    {
                        "index": i,
                        "name": device["name"],
                        "channels": total_channels,
                        "max_input_channels": device["max_input_channels"],
                        "max_output_channels": device["max_output_channels"],
                        "default_samplerate": device["default_samplerate"],
                        "hostapi": device["hostapi"],
                    }
                )
            return device_list
        except Exception as e:
            logger.error(f"Failed to list audio devices: {e}")
            return []

    def get_default_input_device(self) -> Optional[dict]:
        """Get the default input device."""
        try:
            device = sd.query_devices(kind="input")
            # Calculate total channels (input + output)
            total_channels = device["max_input_channels"] + device["max_output_channels"]
            return {
                "index": device["index"],
                "name": device["name"],
                "channels": total_channels,
                "default_samplerate": device["default_samplerate"],
            }
        except Exception as e:
            logger.error(f"Failed to get default input device: {e}")
            return None

    def get_default_output_device(self) -> Optional[dict]:
        """Get the default output device."""
        try:
            device = sd.query_devices(kind="output")
            # Calculate total channels (input + output)
            total_channels = device["max_input_channels"] + device["max_output_channels"]
            return {
                "index": device["index"],
                "name": device["name"],
                "channels": total_channels,
                "default_samplerate": device["default_samplerate"],
            }
        except Exception as e:
            logger.error(f"Failed to get default output device: {e}")
            return None

    def initialize_wake_word_detection(self) -> bool:
        """
        Initialize wake word detection using OpenWakeWord with custom "Hey HENRY" model.

        Downloads required OpenWakeWord resource models (one-time download) if needed,
        then loads the custom trained model from the model/ directory.
        Supports both ONNX and TFLite formats (prefers TFLite for better compatibility).

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not self.audio_enabled:
            logger.info("Audio disabled, skipping wake word detection initialization")
            return False

        try:
            logger.info(f"Initializing wake word detection for: {self.wake_word}")

            # Download required OpenWakeWord resource models (melspectrogram, etc.)
            # This is a one-time download or will skip if already downloaded
            try:
                logger.info("Downloading OpenWakeWord resource models (if needed)...")
                openwakeword.utils.download_models()
                logger.info("OpenWakeWord resource models ready")
            except Exception as download_error:
                logger.warning(
                    f"Failed to download OpenWakeWord resource models: {download_error}. "
                    "Continuing anyway - models may already be downloaded."
                )
                # Continue anyway - models might already be downloaded

            # Find the project root (assumes we're in backend/services or project root)
            project_root = Path(__file__).parent.parent.parent
            model_dir = project_root / "model"

            # Check for custom model files (prefer TFLite for better compatibility, fallback to ONNX)
            onnx_model = model_dir / "hey_henry.onnx"
            tflite_model = model_dir / "hey_henry.tflite"

            model_path = None
            inference_framework = None

            # Prefer TFLite as it's more reliable and doesn't require ONNX runtime dependencies
            if tflite_model.exists():
                model_path = str(tflite_model.resolve())
                inference_framework = "tflite"
                logger.info(f"Found TFLite model: {model_path}")
            elif onnx_model.exists():
                model_path = str(onnx_model.resolve())
                inference_framework = "onnx"
                logger.info(f"Found ONNX model: {model_path}")
                logger.warning(
                    "ONNX models require additional dependencies. "
                    "If loading fails, consider using TFLite format instead."
                )
            else:
                logger.error(
                    f"No custom model found in {model_dir}. "
                    "Expected model files: hey_henry.tflite or hey_henry.onnx"
                )
                logger.error(
                    "Please ensure your custom wake word model is placed in the model/ directory."
                )
                return False

            # Initialize OpenWakeWord with ONLY the custom model
            # Must specify inference_framework for ONNX models
            try:
                if inference_framework == "onnx":
                    # For ONNX models, explicitly specify the inference framework
                    self._oww_model = Model(
                        wakeword_models=[model_path],
                        inference_framework="onnx",
                    )
                else:
                    # For TFLite models, use default (tflite) framework
                    self._oww_model = Model(
                        wakeword_models=[model_path],
                    )
                
                logger.info(
                    f"Wake word detection initialized with custom model: {model_path} "
                    f"(framework: {inference_framework})"
                )
                # Clear target model name when using custom model
                self._target_model_name = None
                return True
            except Exception as model_error:
                error_msg = str(model_error)
                logger.error(
                    f"Failed to load custom model {model_path}: {error_msg}"
                )
                
                # Provide more specific error guidance
                if inference_framework == "onnx":
                    if "melspectrogram.onnx" in error_msg or "NO_SUCHFILE" in error_msg:
                        logger.error(
                            "ONNX model requires OpenWakeWord's internal resources. "
                            "This may indicate an incomplete OpenWakeWord installation or missing dependencies."
                        )
                        logger.info(
                            "Suggestion: Use TFLite format (hey_henry.tflite) instead, "
                            "or reinstall openwakeword: poetry install"
                        )
                    else:
                        logger.error(
                            "Make sure ONNX Runtime is installed and the model file is valid."
                        )
                else:
                    logger.error(
                        "Make sure the TFLite model file is valid and TensorFlow Lite is properly configured."
                    )
                
                # If ONNX failed and TFLite is also available, suggest trying TFLite
                if inference_framework == "onnx" and tflite_model.exists():
                    logger.info(
                        f"TFLite model found at {tflite_model}. "
                        "Consider renaming or removing the ONNX model to use TFLite instead."
                    )
                
                return False

        except ImportError as e:
            logger.error(
                f"Failed to import OpenWakeWord: {e}. "
                "Install it with: poetry add openwakeword"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing wake word detection: {e}")
            return False

    def initialize_wake_word_detection_default(self, model_name: str) -> bool:
        """
        Initialize wake word detection using OpenWakeWord with a default pre-trained model.

        Downloads required OpenWakeWord resource models if needed, then loads the specified
        default pre-trained model (e.g., "alexa", "jarvis", "hey_mycroft").

        Args:
            model_name: Name of the default model to load. Options:
                       "alexa", "jarvis", "hey_mycroft", "hey_rhasspy", "timer", "weather"

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not self.audio_enabled:
            logger.info("Audio disabled, skipping wake word detection initialization")
            return False

        try:
            logger.info(f"Initializing wake word detection with default model: {model_name}")

            # Download required OpenWakeWord resource models (melspectrogram, etc.)
            # This is a one-time download or will skip if already downloaded
            try:
                logger.info("Downloading OpenWakeWord resource models (if needed)...")
                openwakeword.utils.download_models()
                logger.info("OpenWakeWord resource models ready")
            except Exception as download_error:
                logger.warning(
                    f"Failed to download OpenWakeWord resource models: {download_error}. "
                    "Continuing anyway - models may already be downloaded."
                )

            # Map model names to OpenWakeWord model identifiers
            # Default models are named like "alexa_v0.1", "hey_jarvis_v0.1", etc.
            model_map = {
                "alexa": "alexa_v0.1",
                "jarvis": "hey_jarvis_v0.1",
                "hey_mycroft": "hey_mycroft_v0.1",
                "hey_rhasspy": "hey_rhasspy_v0.1",
                "timer": "timer_v0.1",
                "weather": "weather_v0.1",
            }

            if model_name not in model_map:
                logger.error(
                    f"Unknown default model: {model_name}. "
                    f"Available options: {', '.join(model_map.keys())}"
                )
                return False

            oww_model_name = model_map[model_name]

            # Initialize OpenWakeWord with the default model
            # Try to load just the specified model first
            try:
                # Load only the specified default model
                # OpenWakeWord will find it in its resources directory
                self._oww_model = Model(
                    wakeword_models=[oww_model_name],
                )

                logger.info(
                    f"Wake word detection initialized with default model: {oww_model_name}"
                )
                return True
            except Exception as model_error:
                error_msg = str(model_error)
                logger.warning(
                    f"Failed to load specific model {oww_model_name}: {error_msg}. "
                    "Trying to load all models instead..."
                )
                
                # Fallback: load all models (OpenWakeWord will load all pre-trained models)
                # We'll filter by model name in the detection callback
                try:
                    self._oww_model = Model()
                    logger.info(
                        f"Loaded all default models. Will filter for: {oww_model_name}"
                    )
                    # Store the desired model name for filtering
                    self._target_model_name = oww_model_name
                    return True
                except Exception as fallback_error:
                    logger.error(
                        f"Failed to load default models: {fallback_error}"
                    )
                    logger.error(
                        "Make sure OpenWakeWord models are properly downloaded. "
                        "Try running: openwakeword.utils.download_models()"
                    )
                    return False

        except ImportError as e:
            logger.error(
                f"Failed to import OpenWakeWord: {e}. "
                "Install it with: poetry add openwakeword"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing wake word detection: {e}")
            return False

    def detect_wake_word(self, audio_frame: np.ndarray) -> bool:
        """
        Detect wake word in audio frame.

        OpenWakeWord expects audio as numpy array with:
        - Sample rate: 16kHz
        - Format: 16-bit PCM (int16) or float32
        - Shape: (num_samples,) - mono audio

        Args:
            audio_frame: Audio frame as numpy array (16-bit PCM or float32)

        Returns:
            bool: True if wake word detected
        """
        if not self.audio_enabled or not self._oww_model:
            return False

        try:
            # Ensure audio is in the correct format
            # OpenWakeWord expects float32 in range [-1.0, 1.0]
            if audio_frame.dtype != np.float32:
                # Convert int16 to float32
                if audio_frame.dtype == np.int16:
                    audio_frame = audio_frame.astype(np.float32) / 32768.0
                else:
                    audio_frame = audio_frame.astype(np.float32)

            # Ensure mono audio (single channel)
            if len(audio_frame.shape) > 1:
                audio_frame = audio_frame[:, 0] if audio_frame.shape[1] > 0 else audio_frame.flatten()

            # Predict wake word
            # OpenWakeWord returns predictions as a dict with model names as keys
            # For custom models, the key is typically the filename without extension (e.g., "hey_henry")
            predictions = self._oww_model.predict(audio_frame)

            # Check if wake word was detected
            # Threshold of 0.5 is a reasonable default, can be adjusted
            threshold = 0.5
            
            # Look for our custom model first (hey_henry), then check any other models
            custom_model_names = ["hey_henry", "hey henry", self.wake_word.lower()]
            
            for model_name, score in predictions.items():
                # Check if this matches our custom wake word
                model_name_lower = model_name.lower()
                if any(custom_name in model_name_lower for custom_name in custom_model_names):
                    if score > threshold:
                        logger.info(f"Wake word '{self.wake_word}' detected! Model: {model_name} (confidence: {score:.2f})")
                        return True
                # Also check any model above threshold (fallback for default models)
                elif score > threshold:
                    logger.debug(f"Wake word detected: {model_name} (score: {score:.2f})")
                    return True

            return False
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            return False

    def set_input_device(self, device_index: int) -> bool:
        """
        Set the input device.

        Args:
            device_index: Device index

        Returns:
            bool: True if successful
        """
        try:
            devices = sd.query_devices()
            if device_index >= len(devices):
                logger.error(f"Invalid device index: {device_index}")
                return False
            self._current_input_device = device_index
            logger.info(f"Set input device to: {devices[device_index]['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to set input device: {e}")
            return False

    def set_output_device(self, device_index: int) -> bool:
        """
        Set the output device.

        Args:
            device_index: Device index

        Returns:
            bool: True if successful
        """
        try:
            devices = sd.query_devices()
            if device_index >= len(devices):
                logger.error(f"Invalid device index: {device_index}")
                return False
            self._current_output_device = device_index
            logger.info(f"Set output device to: {devices[device_index]['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to set output device: {e}")
            return False

    def start_listening(self, callback, stop_event=None, save_audio=False, audio_dir=None, chunk_size=1280) -> None:
        """
        Start continuous audio listening for wake word detection using PyAudio streaming.

        This method uses the OpenWakeWord prediction_buffer approach for more accurate detection.
        When a wake word is detected, the callback is invoked.

        Note: This method blocks until stop_event is set (if provided) or interrupted.
        It should be run in a separate thread.

        Args:
            callback: Callback function to call when wake word is detected.
                     Called as: callback(wake_word_name, confidence_score)
            stop_event: Optional threading.Event to signal when to stop listening.
                       If None, listens until interrupted.
            save_audio: If True, save audio chunks to WAV files for inspection.
            audio_dir: Directory to save audio files. If None, uses 'audio_recordings' in project root.
            chunk_size: Audio chunk size in samples (default: 1280 = 80ms at 16kHz)
        """
        if not self.audio_enabled or not self._oww_model:
            logger.error("Cannot start listening: audio disabled or wake word model not initialized")
            return

        # Check if we can save audio files
        can_save_audio = save_audio and (HAS_SCIPY or HAS_SOUNDFILE)
        if save_audio and not can_save_audio:
            logger.warning("Cannot save audio: scipy or soundfile not installed. Install with: poetry add scipy")
            save_audio = False

        # OpenWakeWord requires 16kHz sample rate
        sample_rate = 16000
        format_type = pyaudio.paInt16
        channels = 1
        
        # Set up audio saving if enabled
        audio_buffer = []
        buffer_duration = 5.0  # Keep 5 seconds of audio in buffer
        buffer_max_samples = int(sample_rate * buffer_duration)
        save_counter = 0
        
        if save_audio:
            if audio_dir is None:
                project_root = Path(__file__).parent.parent.parent
                audio_dir = project_root / "audio_recordings"
            else:
                audio_dir = Path(audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving audio recordings to: {audio_dir}")
        
        # Initialize frame counter and timing for logging
        self._frame_count = 0
        self._start_time = time()
        threshold = getattr(self, '_detection_threshold', 0.5)
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        # Set device if specified
        device_index = None
        if self._current_input_device is not None:
            device_index = self._current_input_device
        
        try:
            # Open microphone stream
            mic_stream = audio.open(
                format=format_type,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk_size,
                input_device_index=device_index
            )
            
            logger.info("Started listening for wake word...")
            logger.info(f"Using prediction_buffer for detection (threshold: {threshold:.2f})")
            
            # Get model names from prediction_buffer (will be populated after first prediction)
            model_names = []
            
            # Main capture loop
            try:
                while True:
                    # Check if we should stop
                    if stop_event and stop_event.is_set():
                        break
                    
                    # Read audio from microphone
                    audio_data = mic_stream.read(chunk_size, exception_on_overflow=False)
                    
                    # Convert bytes to numpy array (int16)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Save audio to buffer if enabled
                    if save_audio:
                        audio_buffer.extend(audio_array.tolist())
                        # Keep buffer size limited
                        if len(audio_buffer) > buffer_max_samples:
                            audio_buffer = audio_buffer[-buffer_max_samples:]
                    
                    # Feed to OpenWakeWord model (takes int16 directly)
                    self._oww_model.predict(audio_array)
                    
                    # Update model names from prediction_buffer after first prediction
                    if not model_names:
                        model_names = list(self._oww_model.prediction_buffer.keys())
                        if model_names:
                            logger.info(f"Loaded models: {', '.join(model_names)}")
                    
                    # Check prediction_buffer for detections
                    self._frame_count += 1
                    
                    # Log predictions every second (~12-13 frames)
                    if self._frame_count % 12 == 0:
                        current_time = time()
                        time_since_start = current_time - self._start_time
                        
                        # Get current scores from prediction_buffer (last value in buffer)
                        pred_scores = {}
                        if model_names:
                            for mdl in model_names:
                                if mdl in self._oww_model.prediction_buffer:
                                    scores = list(self._oww_model.prediction_buffer[mdl])
                                    if len(scores) > 0:
                                        pred_scores[mdl] = scores[-1]
                        
                        if pred_scores:
                            # Format predictions for readable output
                            pred_str = ", ".join([f"{name}: {score:.3f}" for name, score in pred_scores.items()])
                            logger.info(f"[{time_since_start:.1f}s] Predictions: {pred_str} (threshold: {threshold:.2f})")
                        elif self._frame_count == 12:
                            # First second - show that we're waiting for predictions
                            logger.info(f"[{time_since_start:.1f}s] Waiting for predictions... (models: {len(model_names)})")
                        
                        # Save periodic audio sample every 10 seconds (approximately)
                        if save_audio and self._frame_count % 120 == 0 and len(audio_buffer) > 0:
                            try:
                                save_counter += 1
                                timestamp_str = time_module.strftime("%Y%m%d_%H%M%S", time_module.localtime())
                                filename = audio_dir / f"periodic_{timestamp_str}_{save_counter:04d}.wav"
                                # Get last 2 seconds
                                audio_array_to_save = np.array(audio_buffer[-int(sample_rate * 2):], dtype=np.int16)
                                
                                if HAS_SCIPY:
                                    wavfile.write(str(filename), sample_rate, audio_array_to_save)
                                elif HAS_SOUNDFILE:
                                    sf.write(str(filename), audio_array_to_save, sample_rate)
                                
                                logger.info(f"Saved periodic audio sample to: {filename}")
                            except Exception as e:
                                logger.error(f"Failed to save periodic audio file: {e}")
                    
                    # Check for wake word detections using prediction_buffer
                    # Only check if we have model names (after first prediction)
                    if model_names:
                        for mdl in model_names:
                            # Filter by target model if specified
                            if self._target_model_name and self._target_model_name not in mdl:
                                continue
                            
                            if mdl in self._oww_model.prediction_buffer:
                                scores = list(self._oww_model.prediction_buffer[mdl])
                                if len(scores) > 0:
                                    current_score = scores[-1]
                                    
                                    if current_score > threshold:
                                        logger.info(f"Wake word detected: {mdl} (confidence: {current_score:.2f})")
                                        
                                        # Save audio when wake word detected
                                        if save_audio and len(audio_buffer) > 0:
                                            try:
                                                save_counter += 1
                                                timestamp_str = time_module.strftime("%Y%m%d_%H%M%S", time_module.localtime())
                                                filename = audio_dir / f"detection_{timestamp_str}_{mdl}_{current_score:.2f}.wav"
                                                audio_array_to_save = np.array(audio_buffer, dtype=np.int16)
                                                
                                                if HAS_SCIPY:
                                                    wavfile.write(str(filename), sample_rate, audio_array_to_save)
                                                elif HAS_SOUNDFILE:
                                                    sf.write(str(filename), audio_array_to_save, sample_rate)
                                                
                                                logger.info(f"Saved audio to: {filename}")
                                                # Clear buffer after saving
                                                audio_buffer = []
                                            except Exception as e:
                                                logger.error(f"Failed to save audio file: {e}")
                                        
                                        callback(mdl, float(current_score))
                                        
                                        # Small delay to avoid multiple rapid detections
                                        sleep(0.1)
                    
            except KeyboardInterrupt:
                logger.info("Wake word listening interrupted")
            finally:
                # Cleanup
                mic_stream.stop_stream()
                mic_stream.close()
                audio.terminate()
                
        except Exception as e:
            logger.error(f"Error in audio listening loop: {e}")
            audio.terminate()
            raise

    def cleanup(self) -> None:
        """Clean up audio resources."""
        if self._oww_model:
            # OpenWakeWord models don't need explicit cleanup
            # But we can clear the reference
            self._oww_model = None
            logger.info("Cleaned up wake word detection")


