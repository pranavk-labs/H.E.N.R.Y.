#!/usr/bin/env python3
"""Test script for Piper TTS audio output."""

import sys
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

print("=== Step 1: Test sounddevice basic playback ===")
try:
    import sounddevice as sd
    import numpy as np

    print("Available audio devices:")
    print(sd.query_devices())
    print()

    print("Default output device:")
    default_out = sd.query_devices(kind="output")
    print(f"  Name: {default_out['name']}")
    print(f"  Index: {default_out['index']}")
    print()

    # Test with a simple sine wave
    print("Playing test tone (440 Hz for 1 second)...")
    sample_rate = 22050  # Lower sample rate, same as Piper often uses
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3

    print(f"Audio data: shape={audio.shape}, dtype={audio.dtype}, min={audio.min():.3f}, max={audio.max():.3f}")
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
    print("✓ Test tone playback completed")
    print()

except Exception as e:
    print(f"✗ sounddevice test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=== Step 2: Test Piper TTS synthesis (no playback) ===")
try:
    from piper import PiperVoice
    from pathlib import Path
    import tempfile
    import wave

    # Find Piper model
    home = Path.home()
    model_path = home / ".local/share/piper/voices/en_US-lessac-medium.onnx"

    if not model_path.exists():
        print(f"✗ Piper model not found at: {model_path}")
        sys.exit(1)

    print(f"Loading Piper model: {model_path}")
    voice = PiperVoice.load(str(model_path))
    print("✓ Piper model loaded")
    print()

    # Synthesize to WAV file
    print("Synthesizing: Hello, this is a test")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    import os
    os.close(tmp_fd)

    with wave.open(tmp_path, "wb") as wav_file:
        voice.synthesize_wav("Hello, this is a test", wav_file)

    print(f"✓ WAV file created: {tmp_path}")

    # Check WAV file properties
    import os
    file_size = os.path.getsize(tmp_path)
    print(f"  File size: {file_size} bytes")

    with wave.open(tmp_path, "rb") as wav_file:
        print(f"  Sample rate: {wav_file.getframerate()}")
        print(f"  Channels: {wav_file.getnchannels()}")
        print(f"  Sample width: {wav_file.getsampwidth()}")
        print(f"  Frames: {wav_file.getnframes()}")
    print()

    # Load and check audio data
    try:
        import soundfile as sf
        audio_data, sr = sf.read(tmp_path)
        print(f"Loaded audio with soundfile: shape={audio_data.shape}, dtype={audio_data.dtype}, sr={sr}")
    except ImportError:
        from scipy.io import wavfile
        sr, audio_data = wavfile.read(tmp_path)
        print(f"Loaded audio with scipy: shape={audio_data.shape}, dtype={audio_data.dtype}, sr={sr}")

    print(f"  Audio range: min={audio_data.min():.3f}, max={audio_data.max():.3f}")
    print()

    # Clean up
    os.unlink(tmp_path)

except Exception as e:
    print(f"✗ Piper synthesis test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=== Step 3: Test complete Piper TTS with playback ===")
try:
    from piper import PiperVoice
    from pathlib import Path
    import tempfile
    import wave
    import sounddevice as sd
    import numpy as np

    # Load model
    home = Path.home()
    model_path = home / ".local/share/piper/voices/en_US-lessac-medium.onnx"
    voice = PiperVoice.load(str(model_path))

    # Synthesize
    print("Synthesizing and playing: Testing one two three")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    import os
    os.close(tmp_fd)

    with wave.open(tmp_path, "wb") as wav_file:
        voice.synthesize_wav("Testing one two three", wav_file)

    # Load audio
    try:
        import soundfile as sf
        audio_data, sample_rate = sf.read(tmp_path)
    except ImportError:
        from scipy.io import wavfile
        sample_rate, audio_data = wavfile.read(tmp_path)

    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = audio_data[:, 0]

    # Convert to float32 if needed
    if audio_data.dtype != np.float32:
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32767.0
        else:
            audio_data = audio_data.astype(np.float32)

    print(f"Playing audio: {len(audio_data)} samples at {sample_rate} Hz")
    print(f"  Audio format: shape={audio_data.shape}, dtype={audio_data.dtype}")
    print(f"  Audio range: min={audio_data.min():.3f}, max={audio_data.max():.3f}")

    # Play audio
    sd.play(audio_data, samplerate=sample_rate)
    sd.wait()

    print("✓ Piper TTS playback completed")
    print()

    # Clean up
    os.unlink(tmp_path)

except Exception as e:
    print(f"✗ Piper TTS playback failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=== All tests passed! ===")
print("If you heard all audio (test tone + two TTS messages), Piper TTS is working correctly.")
print("If you heard the test tone but NOT the TTS, there may be an issue with:")
print("  1. Piper audio synthesis (check WAV file properties above)")
print("  2. Audio format conversion (check dtype and range)")
print("  3. Sample rate mismatch")
