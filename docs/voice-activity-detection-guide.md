# Voice Activity Detection (VAD) Implementation Guide

This guide explains how to implement Voice Activity Detection (VAD) to record audio until the user stops talking, instead of using a fixed duration.

## Current Implementation

Currently, `henry_app.py` uses a **fixed 3-second recording** after wake word detection:

```python
# scripts/henry_app.py:340
audio_data = self._record_audio(duration_seconds=3.0)
```

This means if you say "Hey Henry, what's the weather like today?" but finish in 2 seconds, you get 1 second of silence. If you take 4 seconds, your sentence gets cut off.

## Solution: Voice Activity Detection (VAD)

VAD detects when speech starts and stops by analyzing audio energy/patterns. This allows recording to continue as long as you're speaking and stop shortly after you finish.

## Implementation Options

### Option 1: webrtcvad (Lightweight, Fast)

**Best for:** Raspberry Pi, resource-constrained devices

```bash
# Install
poetry add webrtcvad
```

**Pros:**
- Very lightweight (<1MB)
- Fast, efficient
- Works well on Raspberry Pi
- No GPU needed

**Cons:**
- Less sophisticated than deep learning models
- May have more false positives/negatives
- Fixed aggressiveness levels (0-3)

**Implementation:**

```python
import webrtcvad
import collections

def _record_audio_with_vad(
    self,
    sample_rate: int = 16000,
    max_duration: float = 30.0,
    silence_duration: float = 1.5
) -> Optional[Tuple[bytes, int]]:
    """Record audio until silence detected using VAD.

    Args:
        sample_rate: Sample rate in Hz (must be 8000, 16000, 32000, or 48000 for webrtcvad)
        max_duration: Maximum recording duration in seconds (safety limit)
        silence_duration: Seconds of silence before stopping recording

    Returns:
        Tuple of (audio_bytes, sample_rate) or None if recording failed
    """
    if not HAS_PYAUDIO:
        logger.error("PyAudio not available")
        return None

    try:
        # Initialize VAD
        vad = webrtcvad.Vad()
        vad.set_mode(2)  # Aggressiveness: 0-3 (0=least aggressive, 3=most aggressive)

        audio = pyaudio.PyAudio()
        chunk_duration_ms = 30  # webrtcvad works with 10, 20, or 30ms frames
        chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        format_type = pyaudio.paInt16
        channels = 1

        device_index = self.audio_service._current_input_device

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
        silence_chunks = int(silence_duration * 1000 / chunk_duration_ms)  # Convert to chunks
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
                speech_frames.append(chunk)
                ring_buffer.append((chunk, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])

                # If majority of recent frames are silence, we're done
                if num_unvoiced > 0.8 * ring_buffer.maxlen:
                    logger.info(f"Silence detected, stopping recording (duration: {chunk_count * chunk_duration_ms / 1000:.1f}s)")
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
        return None
```

### Option 2: Silero VAD (Most Accurate)

**Best for:** Desktop development, higher accuracy needed

```bash
# Install
poetry add torch onnxruntime
```

**Pros:**
- Deep learning-based (much more accurate)
- Better at distinguishing speech from noise
- Can detect multiple speakers
- Works with any sample rate

**Cons:**
- Larger model size (~5MB)
- Requires torch/onnxruntime
- Slower than webrtcvad (still fast enough)
- May be heavy for Raspberry Pi

**Implementation:**

```python
import torch
from typing import Tuple, Optional

def _record_audio_with_silero_vad(
    self,
    sample_rate: int = 16000,
    max_duration: float = 30.0,
    silence_duration: float = 1.0
) -> Optional[Tuple[bytes, int]]:
    """Record audio until silence detected using Silero VAD.

    Args:
        sample_rate: Sample rate in Hz (8000 or 16000 recommended)
        max_duration: Maximum recording duration in seconds
        silence_duration: Seconds of silence before stopping

    Returns:
        Tuple of (audio_bytes, sample_rate) or None if recording failed
    """
    if not HAS_PYAUDIO:
        logger.error("PyAudio not available")
        return None

    try:
        # Load Silero VAD model (do this once in __init__ for efficiency)
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False)
        (get_speech_timestamps, _, _, _, _) = utils

        audio = pyaudio.PyAudio()
        chunk_size = 512  # Silero works with any chunk size
        format_type = pyaudio.paInt16
        channels = 1

        device_index = self.audio_service._current_input_device

        stream = audio.open(
            format=format_type,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk_size,
            input_device_index=device_index,
        )

        logger.info("Recording with Silero VAD...")

        frames = []
        silence_chunks = int(silence_duration * sample_rate / chunk_size)
        max_chunks = int(max_duration * sample_rate / chunk_size)

        consecutive_silence = 0
        speech_detected = False

        for _ in range(max_chunks):
            if self._shutdown_requested:
                break

            chunk = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(chunk)

            # Convert to tensor for VAD
            audio_int16 = np.frombuffer(chunk, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float32)

            # Run VAD on chunk
            speech_prob = model(audio_tensor, sample_rate).item()

            if speech_prob > 0.5:  # Threshold for speech detection
                speech_detected = True
                consecutive_silence = 0
            elif speech_detected:
                consecutive_silence += 1

                if consecutive_silence >= silence_chunks:
                    logger.info(f"Silence detected, stopping recording")
                    break

        stream.stop_stream()
        stream.close()
        audio.terminate()

        if not speech_detected:
            logger.warning("No speech detected")
            return None

        audio_bytes = b''.join(frames)
        logger.info(f"Recorded {len(audio_bytes)} bytes with Silero VAD")
        return (audio_bytes, sample_rate)

    except Exception as e:
        logger.error(f"Error during Silero VAD recording: {e}", exc_info=True)
        return None
```

## Integration Steps

1. **Choose your VAD implementation** (webrtcvad for Pi, Silero for desktop)

2. **Add the new method** to `VoiceLoop` class in `scripts/henry_app.py`

3. **Update `_get_user_input` method**:

```python
def _get_user_input(self) -> str:
    """Get user input via STT transcription with VAD."""
    if self.stt_service.engine in ("none", "dummy"):
        # ... typed input fallback ...
        pass

    # Use VAD-based recording instead of fixed duration
    audio_data = self._record_audio_with_vad(
        sample_rate=16000,
        max_duration=30.0,  # Safety limit
        silence_duration=1.5  # Stop after 1.5s of silence
    )

    if audio_data is None:
        logger.warning("Failed to record audio with VAD")
        return ""

    # ... rest of transcription code ...
```

4. **Add configuration to settings.py**:

```python
# Voice recording configuration
vad_silence_duration: float = Field(default=1.5, alias="VAD_SILENCE_DURATION")
vad_max_duration: float = Field(default=30.0, alias="VAD_MAX_DURATION")
```

5. **Update .env files**:

```bash
# Voice Activity Detection settings
VAD_SILENCE_DURATION=1.5  # Seconds of silence before stopping
VAD_MAX_DURATION=30.0      # Maximum recording duration (safety limit)
```

## Recommended Settings

### For Raspberry Pi (webrtcvad):
```python
vad.set_mode(2)              # Aggressiveness: 2 (balanced)
silence_duration = 1.5       # 1.5 seconds of silence
max_duration = 30.0          # 30 second maximum
```

### For Desktop (Silero VAD):
```python
speech_threshold = 0.5       # Speech probability threshold
silence_duration = 1.0       # 1 second of silence
max_duration = 30.0          # 30 second maximum
```

## Testing Tips

1. **Test with different aggressiveness levels** (webrtcvad): Mode 0-3
   - Mode 0: Least aggressive (catches more speech, more false positives)
   - Mode 3: Most aggressive (misses some speech, fewer false positives)

2. **Adjust silence duration** based on speaking style:
   - Fast talkers: 1.0s silence
   - Normal pace: 1.5s silence
   - Thoughtful pauses: 2.0s silence

3. **Add logging** to see when speech is detected:
   ```python
   logger.debug(f"VAD: speech={is_speech}, triggered={triggered}, silence_count={num_unvoiced}")
   ```

4. **Test edge cases**:
   - Background noise
   - Music playing
   - Multiple speakers
   - Sudden loud sounds

## Performance Considerations

- **webrtcvad**: ~0.1ms per 30ms frame (negligible CPU)
- **Silero VAD**: ~5-10ms per chunk on CPU (still real-time)
- Both are fast enough for real-time processing
- Pre-load models in `__init__` to avoid startup delay

## Fallback Strategy

Keep the fixed-duration recording as a fallback:

```python
def _get_user_input(self) -> str:
    # Try VAD first
    try:
        audio_data = self._record_audio_with_vad()
        if audio_data:
            return self._transcribe(audio_data)
    except Exception as e:
        logger.warning(f"VAD failed, falling back to fixed duration: {e}")

    # Fallback to fixed duration
    audio_data = self._record_audio(duration_seconds=5.0)
    return self._transcribe(audio_data)
```

## Next Steps

1. Choose webrtcvad or Silero VAD based on your target hardware
2. Add the implementation to `scripts/henry_app.py`
3. Test with various speaking patterns and noise levels
4. Tune parameters (aggressiveness, silence duration) for best results
5. Add configuration to `.env` files for easy adjustment
