#!/bin/bash
# Debug script for TTS audio issues on Raspberry Pi

PI_USER="${PI_USER:-pranavk}"
PI_HOST="${PI_HOST:-100.111.62.95}"
PI_PATH="${PI_PATH:-/home/pranavk/H.E.N.R.Y.}"

echo "=========================================="
echo "H.E.N.R.Y. TTS Audio Debugging"
echo "=========================================="
echo "Target: ${PI_USER}@${PI_HOST}:${PI_PATH}"
echo ""

# Load configuration from .env.deploy if it exists
if [ -f ".env.deploy" ]; then
    echo "Loading configuration from .env.deploy..."
    set -a
    source .env.deploy
    set +a
fi

echo "Step 1: Check recent service logs for TTS-related errors"
echo "=========================================="
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "sudo journalctl -u henry.service -n 100 --no-pager" | grep -A 5 -B 5 -i "tts\|speak\|piper\|sounddevice\|audio" || echo "No TTS-related log entries found"
else
    ssh "${PI_USER}@${PI_HOST}" "sudo journalctl -u henry.service -n 100 --no-pager" | grep -A 5 -B 5 -i "tts\|speak\|piper\|sounddevice\|audio" || echo "No TTS-related log entries found"
fi
echo ""

echo "Step 2: Check sounddevice availability and devices"
echo "=========================================="
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry run python -c \"
import sounddevice as sd
print('✓ sounddevice imported successfully')
print()
print('=== Available Audio Devices ===')
print(sd.query_devices())
print()
print('=== Default Output Device ===')
try:
    device = sd.query_devices(kind='output')
    print(f'Default output device: {device[\"name\"]} (index: {device[\"index\"]})')
except Exception as e:
    print(f'Error getting default output device: {e}')
\""
else
    ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry run python -c \"
import sounddevice as sd
print('✓ sounddevice imported successfully')
print()
print('=== Available Audio Devices ===')
print(sd.query_devices())
print()
print('=== Default Output Device ===')
try:
    device = sd.query_devices(kind='output')
    print(f'Default output device: {device[\"name\"]} (index: {device[\"index\"]})')
except Exception as e:
    print(f'Error getting default output device: {e}')
\""
fi
echo ""

echo "Step 3: Test audio playback with sounddevice"
echo "=========================================="
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry run python -c \"
import sounddevice as sd
import numpy as np
import time

print('Generating test tone (440 Hz, 1 second)...')
sample_rate = 44100
duration = 1.0
frequency = 440.0

# Generate sine wave
t = np.linspace(0, duration, int(sample_rate * duration))
audio = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.5

print(f'Playing audio ({len(audio)} samples at {sample_rate} Hz)...')
try:
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
    print('✓ Audio playback successful!')
except Exception as e:
    print(f'✗ Audio playback failed: {e}')
    import traceback
    traceback.print_exc()
\""
else
    ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry run python -c \"
import sounddevice as sd
import numpy as np
import time

print('Generating test tone (440 Hz, 1 second)...')
sample_rate = 44100
duration = 1.0
frequency = 440.0

# Generate sine wave
t = np.linspace(0, duration, int(sample_rate * duration))
audio = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.5

print(f'Playing audio ({len(audio)} samples at {sample_rate} Hz)...')
try:
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
    print('✓ Audio playback successful!')
except Exception as e:
    print(f'✗ Audio playback failed: {e}')
    import traceback
    traceback.print_exc()
\""
fi
echo ""

echo "Step 4: Test Piper TTS end-to-end"
echo "=========================================="
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry run python -c \"
from backend.services.tts_service import TextToSpeechService
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

print('Initializing TTS service...')
tts = TextToSpeechService.get_instance()
print(f'TTS engine: {tts.engine_name}')
print(f'Piper voice loaded: {tts._piper_voice is not None}')
print()

if tts.engine_name == 'piper' and tts._piper_voice:
    print('Testing TTS playback with: Hello, this is a test')
    tts.speak('Hello, this is a test')
    print('✓ TTS speak completed (check if you heard audio)')
else:
    print('✗ Piper TTS not initialized properly')
    print(f'  Expected engine: piper')
    print(f'  Actual engine: {tts.engine_name}')
\""
else
    ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry run python -c \"
from backend.services.tts_service import TextToSpeechService
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

print('Initializing TTS service...')
tts = TextToSpeechService.get_instance()
print(f'TTS engine: {tts.engine_name}')
print(f'Piper voice loaded: {tts._piper_voice is not None}')
print()

if tts.engine_name == 'piper' and tts._piper_voice:
    print('Testing TTS playback with: Hello, this is a test')
    tts.speak('Hello, this is a test')
    print('✓ TTS speak completed (check if you heard audio)')
else:
    print('✗ Piper TTS not initialized properly')
    print(f'  Expected engine: piper')
    print(f'  Actual engine: {tts.engine_name}')
\""
fi
echo ""

echo "Step 5: Check ALSA/PulseAudio configuration"
echo "=========================================="
echo "=== ALSA playback devices ==="
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "aplay -l"
else
    ssh "${PI_USER}@${PI_HOST}" "aplay -l"
fi
echo ""
echo "=== Current volume levels ==="
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "amixer scontents | grep -A 5 'Master\|Headphone\|PCM'" || echo "No volume controls found"
else
    ssh "${PI_USER}@${PI_HOST}" "amixer scontents | grep -A 5 'Master\|Headphone\|PCM'" || echo "No volume controls found"
fi
echo ""

echo "=========================================="
echo "Debug complete!"
echo "=========================================="
echo ""
echo "If audio playback with sounddevice failed:"
echo "1. Check if the default output device is correct"
echo "2. Try setting a specific output device in the code"
echo "3. Check volume levels with: ssh ${PI_USER}@${PI_HOST} 'amixer scontents'"
echo "4. Verify PulseAudio is running: ssh ${PI_USER}@${PI_HOST} 'pulseaudio --check && echo PulseAudio is running'"
echo ""
