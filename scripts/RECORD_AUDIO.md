# How to Record and Test Audio Files

## Quick Start

### 1. Test with Live Microphone

```bash
# Test with custom model (hey_henry.tflite)
poetry run python scripts/test_audio.py

# Test with default 'alexa' model
poetry run python scripts/test_audio.py --default alexa

# Save audio recordings while testing
poetry run python scripts/test_audio.py --default alexa --save-audio

# Adjust detection threshold (lower = more sensitive)
poetry run python scripts/test_audio.py --default alexa --threshold 0.3
```

### 2. Record an Audio File

#### Using `arecord` (Linux):

```bash
# Record 5 seconds of audio at 16kHz mono (required for OpenWakeWord)
arecord -d 5 -r 16000 -c 1 -f S16_LE test_audio.wav

# Record 10 seconds
arecord -d 10 -r 16000 -c 1 -f S16_LE test_audio.wav

# Record with a specific device
arecord -d 5 -r 16000 -c 1 -f S16_LE -D hw:1,0 test_audio.wav
```

#### Using `sox` (if installed):

```bash
# Record 5 seconds
rec -r 16000 -c 1 -t wav test_audio.wav trim 0 5

# Record until Ctrl+C
rec -r 16000 -c 1 -t wav test_audio.wav
```

#### Using Python (scipy/soundfile):

```bash
# Simple recording script
poetry run python -c "
import sounddevice as sd
import soundfile as sf
import numpy as np

duration = 5  # seconds
sample_rate = 16000

print('Recording...')
audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
sd.wait()
print('Done!')

sf.write('test_audio.wav', audio, sample_rate)
print('Saved to test_audio.wav')
"
```

### 3. Test with Recorded File

```bash
# Test with a recorded WAV file
poetry run python scripts/test_audio.py --file test_audio.wav

# With default model
poetry run python scripts/test_audio.py --default alexa --file test_audio.wav

# With custom threshold
poetry run python scripts/test_audio.py --file test_audio.wav --threshold 0.3
```

## Audio Requirements

For OpenWakeWord to work correctly:
- **Sample Rate**: 16000 Hz (16 kHz)
- **Channels**: 1 (mono)
- **Format**: 16-bit PCM (int16) or float32
- **File Format**: WAV

The script will automatically:
- Convert to mono if stereo
- Resample to 16kHz if different rate
- Convert format if needed

## Examples

### Example 1: Quick Test with Alexa Model

```bash
# 1. Record yourself saying "Alexa"
arecord -d 3 -r 16000 -c 1 -f S16_LE alexa_test.wav

# 2. Test the recording
poetry run python scripts/test_audio.py --default alexa --file alexa_test.wav
```

### Example 2: Test Custom Model

```bash
# 1. Record yourself saying "Hey Henry"
arecord -d 3 -r 16000 -c 1 -f S16_LE henry_test.wav

# 2. Test the recording (uses custom model automatically)
poetry run python scripts/test_audio.py --file henry_test.wav
```

### Example 3: Batch Test Multiple Files

```bash
# Record multiple test files
for i in {1..5}; do
    echo "Recording test $i..."
    arecord -d 3 -r 16000 -c 1 -f S16_LE test_$i.wav
done

# Test all files
for file in test_*.wav; do
    echo "Testing $file..."
    poetry run python scripts/test_audio.py --default alexa --file "$file"
done
```

## Troubleshooting

### "File not found"
- Check the path is correct
- Use absolute path: `--file /full/path/to/file.wav`

### "Need soundfile or scipy to load audio files"
```bash
poetry add scipy
```

### Audio plays but no detections
- Try lowering threshold: `--threshold 0.3`
- Check audio format matches requirements
- Verify you're saying the correct wake word for the model

### Wrong sample rate detected
- The script auto-resamples, but for best results record at 16kHz from the start

## Tips

1. **Record in quiet environment** - Background noise can affect detection
2. **Speak clearly** - Pronounce the wake word naturally
3. **Test multiple times** - Wake word detection can vary
4. **Use saved recordings** - Files saved with `--save-audio` can be reused for testing
5. **Check saved files** - Files in `audio_recordings/` can be tested with `--file`

