#!/bin/bash
# Audio setup script for Raspberry Pi
# Run this script ON THE RASPBERRY PI to configure audio devices

set -e

echo "=========================================="
echo "H.E.N.R.Y. Pi Audio Setup"
echo "=========================================="
echo ""

# Get current user
CURRENT_USER=$(whoami)
echo "Setting up audio for user: $CURRENT_USER"
echo ""

# 1. Install system audio libraries
echo "Step 1: Installing system audio libraries..."
sudo apt update
sudo apt install -y \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    pulseaudio \
    pulseaudio-utils

echo "✓ Audio libraries installed"
echo ""

# 2. Add user to audio group
echo "Step 2: Adding user to audio group..."
if groups $CURRENT_USER | grep -q '\baudio\b'; then
    echo "✓ User already in audio group"
else
    sudo usermod -a -G audio $CURRENT_USER
    echo "✓ User added to audio group"
    echo "⚠ WARNING: You must LOG OUT and LOG BACK IN for group changes to take effect!"
    echo "⚠ After logging back in, re-run this script to continue setup."
fi
echo ""

# 3. List audio devices
echo "Step 3: Detecting audio devices..."
echo ""
echo "=== Recording Devices (Microphones) ==="
arecord -l
echo ""
echo "=== Playback Devices (Speakers) ==="
aplay -l
echo ""

# 4. Test if we can access audio devices
echo "Step 4: Testing audio device access..."
echo ""

# Try to record a short test
echo "Testing microphone access (recording 1 second of silence)..."
if arecord -d 1 -f cd /tmp/test_audio.wav 2>/dev/null; then
    echo "✓ Microphone access successful"
    rm -f /tmp/test_audio.wav
else
    echo "✗ Microphone access failed"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if your microphone is plugged in properly"
    echo "2. Make sure you're in the audio group: groups $CURRENT_USER"
    echo "3. If you just added the user to audio group, LOG OUT and LOG BACK IN"
    echo "4. Try running: sudo chmod a+rw /dev/snd/*"
fi
echo ""

# 5. Set default audio device (optional - uncomment if needed)
echo "Step 5: Audio device configuration"
echo ""
echo "To set a specific audio device as default, create ~/.asoundrc with:"
echo ""
echo "pcm.!default {"
echo "    type asym"
echo "    playback.pcm {"
echo "        type plug"
echo "        slave.pcm \"hw:0,0\"  # Change to your device"
echo "    }"
echo "    capture.pcm {"
echo "        type plug"
echo "        slave.pcm \"hw:0,0\"  # Change to your device"
echo "    }"
echo "}"
echo ""
echo "ctl.!default {"
echo "    type hw"
echo "    card 0  # Change to your card number"
echo "}"
echo ""

# 6. Python test script
echo "Step 6: Creating Python audio test script..."
cat > /tmp/test_audio_devices.py << 'EOF'
#!/usr/bin/env python3
"""Test script to verify audio device access with PyAudio."""

import sys

try:
    import pyaudio
    print("✓ PyAudio imported successfully")
except ImportError as e:
    print(f"✗ Failed to import PyAudio: {e}")
    print("Run: poetry install --extras pi")
    sys.exit(1)

try:
    # Initialize PyAudio
    pa = pyaudio.PyAudio()
    print(f"✓ PyAudio initialized (version: {pyaudio.get_portaudio_version_text()})")
    print()

    # List all devices
    print("=== Available Audio Devices ===")
    device_count = pa.get_device_count()
    print(f"Found {device_count} devices:")
    print()

    input_devices = []
    output_devices = []

    for i in range(device_count):
        info = pa.get_device_info_by_index(i)
        device_type = []

        if info['maxInputChannels'] > 0:
            device_type.append("INPUT")
            input_devices.append(i)
        if info['maxOutputChannels'] > 0:
            device_type.append("OUTPUT")
            output_devices.append(i)

        print(f"Device {i}: {info['name']}")
        print(f"  Type: {' + '.join(device_type) if device_type else 'NONE'}")
        print(f"  Max Input Channels: {info['maxInputChannels']}")
        print(f"  Max Output Channels: {info['maxOutputChannels']}")
        print(f"  Default Sample Rate: {info['defaultSampleRate']}")
        print()

    # Test default input device
    print("=== Testing Default Input Device ===")
    try:
        default_input = pa.get_default_input_device_info()
        print(f"✓ Default input device: {default_input['name']} (index: {default_input['index']})")

        # Try to open a stream
        print("Testing microphone access...")
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
            input_device_index=default_input['index']
        )

        # Read a small chunk
        data = stream.read(1024, exception_on_overflow=False)
        stream.stop_stream()
        stream.close()

        print("✓ Successfully opened and read from microphone!")
        print()

    except Exception as e:
        print(f"✗ Failed to access default input device: {e}")
        print()
        print("This is the same error H.E.N.R.Y. is experiencing!")
        print()
        print("Possible solutions:")
        print("1. Make sure you're in the audio group: groups $(whoami)")
        print("2. If not, run: sudo usermod -a -G audio $(whoami)")
        print("3. LOG OUT and LOG BACK IN after adding to audio group")
        print("4. Check device permissions: ls -l /dev/snd/")
        print("5. Try: sudo chmod a+rw /dev/snd/*")
        print()

    # Cleanup
    pa.terminate()

except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

chmod +x /tmp/test_audio_devices.py
echo "✓ Created test script: /tmp/test_audio_devices.py"
echo ""

# 7. Summary
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. If you just added the user to audio group, LOG OUT and LOG BACK IN"
echo ""
echo "2. Run the Python test script to verify PyAudio can access devices:"
echo "   python3 /tmp/test_audio_devices.py"
echo ""
echo "3. If the test script works, re-deploy H.E.N.R.Y.:"
echo "   bash scripts/deploy_to_pi.sh"
echo ""
echo "4. Check the logs:"
echo "   sudo journalctl -u henry.service -f"
echo ""
