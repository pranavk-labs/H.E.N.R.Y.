#!/usr/bin/env python3
"""Simple audio service test script.

Usage:
    # Test with live microphone (custom model)
    poetry run python scripts/test_audio.py

    # Test with default model
    poetry run python scripts/test_audio.py --default alexa

    # Test with a recorded WAV file
    poetry run python scripts/test_audio.py --file path/to/audio.wav

    # Save audio recordings
    poetry run python scripts/test_audio.py --save-audio
"""

import argparse
import sys
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.audio_service import AudioService
from backend.config.settings import get_settings


def test_with_file(audio_service: AudioService, file_path: Path, threshold: float = 0.5):
    """Test wake word detection with a pre-recorded audio file."""
    import numpy as np
    
    try:
        # Try to load with soundfile first, then scipy
        try:
            import soundfile as sf
            audio_data, sample_rate = sf.read(str(file_path))
        except ImportError:
            try:
                from scipy.io import wavfile
                sample_rate, audio_data = wavfile.read(str(file_path))
                # Convert int16 to float32 if needed
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
            except ImportError:
                print("ERROR: Need soundfile or scipy to load audio files")
                print("Install with: poetry add scipy")
                return False
        
        print(f"Loaded audio file: {file_path}")
        print(f"  Sample rate: {sample_rate} Hz")
        print(f"  Duration: {len(audio_data) / sample_rate:.2f} seconds")
        print(f"  Format: {audio_data.dtype}")
        print()
        
        # Convert to mono if needed
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            print(f"Resampling from {sample_rate} Hz to 16000 Hz...")
            try:
                from scipy import signal
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = signal.resample(audio_data, num_samples)
                sample_rate = 16000
            except ImportError:
                print("ERROR: Cannot resample. File must be 16kHz or install scipy")
                print("Install with: poetry add scipy")
                return False
        
        # Convert to int16 for model (OpenWakeWord expects int16)
        if audio_data.dtype != np.int16:
            # Convert float32 [-1, 1] to int16
            audio_data = (audio_data * 32767).astype(np.int16)
        
        # Process audio in chunks (1280 samples = 80ms at 16kHz)
        chunk_size = 1280
        print("Processing audio file...")
        print(f"  Threshold: {threshold}")
        print()
        
        detections = []
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            if len(chunk) < chunk_size:
                # Pad last chunk if needed
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
            
            # Feed to model
            audio_service._oww_model.predict(chunk)
            
            # Check prediction buffer
            for model_name in audio_service._oww_model.prediction_buffer.keys():
                scores = list(audio_service._oww_model.prediction_buffer[model_name])
                if len(scores) > 0:
                    current_score = scores[-1]
                    if current_score > threshold:
                        time_seconds = i / sample_rate
                        detections.append((time_seconds, model_name, current_score))
                        print(f"  [{(time_seconds):.2f}s] Wake word detected: {model_name} (confidence: {current_score:.3f})")
        
        if not detections:
            print("  No wake words detected in the file.")
        else:
            print(f"\n  Total detections: {len(detections)}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to process audio file: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test audio service and wake word detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--default",
        dest="default_model",
        choices=["alexa", "jarvis", "hey_mycroft", "hey_rhasspy", "timer", "weather"],
        help="Use a default pre-trained model instead of custom model",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Test with a pre-recorded WAV file instead of live microphone",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Detection threshold (0.0 to 1.0, default: 0.5)",
    )
    parser.add_argument(
        "--save-audio",
        action="store_true",
        help="Save audio recordings to WAV files (requires scipy or soundfile)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Audio Service Test")
    print("=" * 60)
    print()

    # Get settings and service
    settings = get_settings()
    audio_service = AudioService.get_instance()

    # Check if audio is enabled
    if not settings.audio_enabled:
        print("⚠️  Audio is disabled. Set AUDIO_ENABLED=True in .env.local")
        return

    # Health check
    health = audio_service.health_check()
    if health['status'] != 'healthy':
        print(f"❌ Service unhealthy: {health.get('error', 'Unknown error')}")
        return

    print("✓ Service healthy")
    print()

    # Initialize wake word detection
    print("Initializing wake word detection...")
    if args.default_model:
        initialized = audio_service.initialize_wake_word_detection_default(args.default_model)
        model_name = args.default_model
    else:
        initialized = audio_service.initialize_wake_word_detection()
        model_name = settings.wake_word

    if not initialized:
        print("❌ Failed to initialize wake word detection")
        print("   Check logs above for error details")
        return

    print(f"✓ Initialized (model: {model_name})")
    audio_service._detection_threshold = args.threshold
    print(f"  Threshold: {args.threshold}")
    print()

    # Test with file or live microphone
    if args.file:
        # Test with recorded file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        
        print(f"Testing with audio file: {file_path}")
        print()
        test_with_file(audio_service, file_path, args.threshold)
        
    else:
        # Test with live microphone
        print("Listening for wake word...")
        print("Press Ctrl+C to stop")
        print()
        
        # Enable logging to see predictions and debug info
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            force=True  # Override any existing logging config
        )

        def callback(model_name: str, confidence: float):
            print(f"\n🔊 WAKE WORD DETECTED!")
            print(f"   Model: {model_name}")
            print(f"   Confidence: {confidence:.2%}")
            print()

        stop_event = threading.Event()
        
        listen_thread = threading.Thread(
            target=audio_service.start_listening,
            args=(callback, stop_event, args.save_audio, None),
            daemon=False
        )
        listen_thread.start()
        
        try:
            listen_thread.join()
        except KeyboardInterrupt:
            print("\n\nStopping...")
            stop_event.set()
            listen_thread.join(timeout=2)
        
        audio_service.cleanup()
        print("Done.")


if __name__ == "__main__":
    main()

