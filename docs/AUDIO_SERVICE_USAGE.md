# AudioService Usage Guide

This document shows different ways to test and use the AudioService outside of the test_audio.py script.

## Method 1: Interactive Python Session

Start an interactive Python session with AudioService pre-loaded:

```bash
poetry run python -i scripts/test_audio_interactive.py
```

Then you can use it directly:
```python
# Check health
audio_service.health_check()

# List devices
audio_service.list_devices()

# Initialize wake word detection
audio_service.initialize_wake_word_detection()
# or
audio_service.initialize_wake_word_detection_default('alexa')

# Set threshold
audio_service._detection_threshold = 0.5

# Start listening
import threading
stop_event = threading.Event()

def callback(model_name, confidence):
    print(f"Detected: {model_name} ({confidence:.2%})")

thread = threading.Thread(
    target=audio_service.start_listening,
    args=(callback, stop_event)
)
thread.start()

# Later, stop it:
stop_event.set()
```

## Method 2: Direct Python Import

In any Python script or session:

```python
from backend.services.audio_service import AudioService
from backend.config.settings import get_settings

# Get instance
audio_service = AudioService.get_instance()

# Check if audio is enabled
settings = get_settings()
if not settings.audio_enabled:
    print("Enable audio first: AUDIO_ENABLED=True in .env.local")
    exit()

# Health check
health = audio_service.health_check()
print(health)

# List devices
devices = audio_service.list_devices()
for device in devices:
    print(f"{device['index']}: {device['name']}")

# Initialize with custom model
audio_service.initialize_wake_word_detection()

# Or with default model
# audio_service.initialize_wake_word_detection_default('alexa')

# Set threshold
audio_service._detection_threshold = 0.5

# Start listening with callback
import threading

def on_wake_word(model_name: str, confidence: float):
    print(f"Wake word detected: {model_name} ({confidence:.2%})")
    # Add your custom logic here

stop_event = threading.Event()
thread = threading.Thread(
    target=audio_service.start_listening,
    args=(on_wake_word, stop_event, False, None),  # callback, stop_event, save_audio, audio_dir
    daemon=False
)
thread.start()

# Run for a while...
import time
time.sleep(60)  # Listen for 60 seconds

# Stop
stop_event.set()
thread.join()
audio_service.cleanup()
```

## Method 3: Simple Script

See `scripts/example_audio_usage.py` for a complete example:

```bash
poetry run python scripts/example_audio_usage.py
```

## Method 4: In Your Application Code

### FastAPI Integration Example

```python
from fastapi import FastAPI
from backend.services.audio_service import AudioService
import threading

app = FastAPI()
audio_service = AudioService.get_instance()
stop_listening = threading.Event()

def wake_word_callback(model_name: str, confidence: float):
    """Handle wake word detection."""
    print(f"Wake word detected: {model_name}")
    # Start your voice processing pipeline here

@app.on_event("startup")
async def startup_event():
    """Initialize audio service on startup."""
    if audio_service.audio_enabled:
        # Initialize wake word detection
        audio_service.initialize_wake_word_detection()
        
        # Start listening in background thread
        listen_thread = threading.Thread(
            target=audio_service.start_listening,
            args=(wake_word_callback, stop_listening),
            daemon=True
        )
        listen_thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    stop_listening.set()
    audio_service.cleanup()
```

## Method 5: Quick Test in Python REPL

```bash
poetry run python
```

```python
>>> from backend.services.audio_service import AudioService
>>> service = AudioService.get_instance()
>>> service.health_check()
>>> service.list_devices()
>>> service.initialize_wake_word_detection_default('alexa')
```

## Method 6: Test Individual Methods

You can test individual methods without starting the full listening loop:

```python
from backend.services.audio_service import AudioService
import numpy as np

service = AudioService.get_instance()

# Test with a silent audio frame
silent_audio = np.zeros(1280, dtype=np.int16)
service.detect_wake_word(silent_audio)  # Should return False

# Initialize the model first
service.initialize_wake_word_detection()

# Now test detection (still silent, so should be False)
result = service.detect_wake_word(silent_audio)
print(f"Detection result: {result}")
```

## Available Methods

### Health and Device Management
- `health_check()` - Check audio service health
- `list_devices()` - List all audio devices
- `get_default_input_device()` - Get default input device
- `get_default_output_device()` - Get default output device
- `set_input_device(device_index)` - Set input device
- `set_output_device(device_index)` - Set output device

### Wake Word Detection
- `initialize_wake_word_detection()` - Load custom model
- `initialize_wake_word_detection_default(model_name)` - Load default model
- `start_listening(callback, stop_event, save_audio, audio_dir, chunk_size)` - Start listening
- `detect_wake_word(audio_frame)` - Detect wake word in a single frame
- `cleanup()` - Clean up resources

## Callback Function Signature

Your callback function should accept:
```python
def my_callback(model_name: str, confidence: float):
    """
    Args:
        model_name: Name of the model that detected the wake word
        confidence: Confidence score (0.0 to 1.0)
    """
    print(f"Wake word detected: {model_name} with {confidence:.2%} confidence")
```

## Stop Event

Use a `threading.Event` to control when listening stops:

```python
import threading

stop_event = threading.Event()

# Start listening
thread = threading.Thread(
    target=audio_service.start_listening,
    args=(callback, stop_event)
)
thread.start()

# Later, stop it:
stop_event.set()
thread.join()  # Wait for thread to finish
```

## Configuration

Make sure `AUDIO_ENABLED=True` is set in your `.env.local` file:

```bash
echo "AUDIO_ENABLED=True" >> .env.local
```

Or set it directly in your environment:
```bash
export AUDIO_ENABLED=True
poetry run python your_script.py
```

