#!/bin/bash
# Watch TTS logs in real-time

PI_USER="${PI_USER:-pranavk}"
PI_HOST="${PI_HOST:-100.111.62.95}"
PI_PASSWORD="${PI_PASSWORD:-Passw0rd}"

# Load configuration from .env.deploy if it exists
if [ -f ".env.deploy" ]; then
    set -a
    source .env.deploy
    set +a
fi

echo "Watching HENRY TTS logs (Press Ctrl+C to stop)..."
echo "Try saying 'Hey HENRY' and ask a question..."
echo ""

if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "sudo journalctl -u henry.service -f --no-pager" | grep --line-buffered -i "tts\|speak\|piper\|sounddevice\|Assistant response"
else
    ssh "${PI_USER}@${PI_HOST}" "sudo journalctl -u henry.service -f --no-pager" | grep --line-buffered -i "tts\|speak\|piper\|sounddevice\|Assistant response"
fi
