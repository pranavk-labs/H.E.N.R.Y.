#!/bin/bash
# Deployment script for Raspberry Pi (Voice Interface Client)

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load configuration from .env.deploy if it exists
if [ -f "${PROJECT_ROOT}/.env.deploy" ]; then
    echo "Loading configuration from .env.deploy..."
    set -a  # automatically export all variables
    source "${PROJECT_ROOT}/.env.deploy"
    set +a
fi

# Configuration (with defaults)
PI_USER="${PI_USER:-pi}"
PI_HOST="${PI_HOST:-raspberrypi.local}"
PI_PATH="${PI_PATH:-/home/pi/H.E.N.R.Y.}"
PI_PASSWORD="${PI_PASSWORD:-}"

# Check if sshpass is available for password automation
if [ -n "$PI_PASSWORD" ] && ! command -v sshpass &> /dev/null; then
    echo "Warning: PI_PASSWORD set but sshpass not installed."
    echo "Install with: sudo apt install sshpass  (or brew install hudochenkov/sshpass/sshpass on macOS)"
    echo "Falling back to interactive password prompts."
    PI_PASSWORD=""
fi

echo "==========================================="
echo "H.E.N.R.Y. Raspberry Pi Deployment"
echo "==========================================="
echo "Target: ${PI_USER}@${PI_HOST}:${PI_PATH}"
echo "Note: Pi runs GUI + voice interface (combined app)"
echo "      Backend API must be running on server"
echo ""

# Check if SSH key is available
if [ -z "$PI_PASSWORD" ] && [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Warning: No SSH key found. You may need to enter password."
fi

# Create remote directory
echo "Creating remote directory..."
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${PI_PATH}"
else
    ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${PI_PATH}"
fi

# Cleanup old cache and build artifacts before deployment
echo "Cleaning up old cache and artifacts..."
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "
        cd ${PI_PATH} 2>/dev/null || exit 0
        echo 'Removing Python cache files...'
        find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name '*.pyc' -delete 2>/dev/null || true
        find . -type f -name '*.pyo' -delete 2>/dev/null || true
        echo 'Cleaning poetry cache (keeping virtual environment)...'
        rm -rf ~/.cache/pypoetry/cache 2>/dev/null || true
        rm -rf ~/.cache/pypoetry/artifacts 2>/dev/null || true
        echo 'Cleanup complete.'
    "
else
    ssh "${PI_USER}@${PI_HOST}" "
        cd ${PI_PATH} 2>/dev/null || exit 0
        echo 'Removing Python cache files...'
        find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name '*.pyc' -delete 2>/dev/null || true
        find . -type f -name '*.pyo' -delete 2>/dev/null || true
        echo 'Cleaning poetry cache (keeping virtual environment)...'
        rm -rf ~/.cache/pypoetry/cache 2>/dev/null || true
        rm -rf ~/.cache/pypoetry/artifacts 2>/dev/null || true
        echo 'Cleanup complete.'
    "
fi

# Copy files (excluding unnecessary files and Docker-related files)
echo "Copying files..."
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" rsync -avz \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env.local' \
        --exclude='.env.server' \
        --exclude='data/' \
        --exclude='*.db' \
        --exclude='.pytest_cache' \
        --exclude='.mypy_cache' \
        --exclude='venv/' \
        --exclude='.venv/' \
        --exclude='Dockerfile' \
        --exclude='docker-compose.yml' \
        --exclude='.dockerignore' \
        "${PROJECT_ROOT}/" "${PI_USER}@${PI_HOST}:${PI_PATH}/"
else
    rsync -avz \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env.local' \
        --exclude='.env.server' \
        --exclude='data/' \
        --exclude='*.db' \
        --exclude='.pytest_cache' \
        --exclude='.mypy_cache' \
        --exclude='venv/' \
        --exclude='.venv/' \
        --exclude='Dockerfile' \
        --exclude='docker-compose.yml' \
        --exclude='.dockerignore' \
        "${PROJECT_ROOT}/" "${PI_USER}@${PI_HOST}:${PI_PATH}/"
fi

# Install dependencies on Pi (with pi extras for audio support)
echo "Installing dependencies on Pi (with audio support)..."
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh "${PI_USER}@${PI_HOST}" "bash -l -c 'cd ${PI_PATH} && poetry lock --no-interaction --no-ansi && poetry install --without dev --extras pi --no-root --no-ansi --no-interaction'"
else
    ssh "${PI_USER}@${PI_HOST}" "bash -l -c 'cd ${PI_PATH} && poetry lock --no-interaction --no-ansi && poetry install --without dev --extras pi --no-root --no-ansi --no-interaction'"
fi

# Copy .env.pi if it exists
if [ -f "${PROJECT_ROOT}/.env.pi" ]; then
    echo "Copying .env.pi..."
    if [ -n "$PI_PASSWORD" ]; then
        sshpass -p "$PI_PASSWORD" scp "${PROJECT_ROOT}/.env.pi" "${PI_USER}@${PI_HOST}:${PI_PATH}/.env"
    else
        scp "${PROJECT_ROOT}/.env.pi" "${PI_USER}@${PI_HOST}:${PI_PATH}/.env"
    fi
fi

# Setup systemd service
echo "Setting up systemd service..."
# Generate service file with correct paths and user
TEMP_SERVICE=$(mktemp)
cat > "$TEMP_SERVICE" << EOF
[Unit]
Description=H.E.N.R.Y. GUI and Voice Interface
After=network.target sound.target graphical.target

[Service]
Type=simple
User=${PI_USER}
WorkingDirectory=${PI_PATH}
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/${PI_USER}/.Xauthority"
ExecStart=/usr/bin/env bash -l -c 'cd ${PI_PATH} && poetry run python scripts/henry_app.py'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

# Copy generated service file to Pi temporarily
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" scp "$TEMP_SERVICE" "${PI_USER}@${PI_HOST}:/tmp/henry.service"
else
    scp "$TEMP_SERVICE" "${PI_USER}@${PI_HOST}:/tmp/henry.service"
fi
rm "$TEMP_SERVICE"

# Configure journal log rotation to save SSD space
echo "Configuring log rotation..."
TEMP_JOURNAL_CONF=$(mktemp)
cat > "$TEMP_JOURNAL_CONF" << 'EOF'
# H.E.N.R.Y. Journal Configuration
# Limits journal size to prevent filling SSD
[Journal]
SystemMaxUse=100M
SystemKeepFree=500M
SystemMaxFileSize=10M
MaxRetentionSec=7day
MaxFileSec=1day
EOF

if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" scp "$TEMP_JOURNAL_CONF" "${PI_USER}@${PI_HOST}:/tmp/henry-journal.conf"
else
    scp "$TEMP_JOURNAL_CONF" "${PI_USER}@${PI_HOST}:/tmp/henry-journal.conf"
fi
rm "$TEMP_JOURNAL_CONF"

# Install and enable service (all in one session to avoid multiple password prompts)
echo "Installing and restarting service..."
if [ -n "$PI_PASSWORD" ]; then
    sshpass -p "$PI_PASSWORD" ssh -t "${PI_USER}@${PI_HOST}" "
        echo '${PI_PASSWORD}' | sudo -S mv /tmp/henry.service /etc/systemd/system/henry.service
        echo '${PI_PASSWORD}' | sudo -S mv /tmp/henry-journal.conf /etc/systemd/journald.conf.d/henry.conf
        echo '${PI_PASSWORD}' | sudo -S mkdir -p /etc/systemd/journald.conf.d
        echo '${PI_PASSWORD}' | sudo -S mv /tmp/henry-journal.conf /etc/systemd/journald.conf.d/henry.conf 2>/dev/null || true
        echo '${PI_PASSWORD}' | sudo -S systemctl daemon-reload
        echo '${PI_PASSWORD}' | sudo -S systemctl restart systemd-journald
        echo '${PI_PASSWORD}' | sudo -S systemctl enable henry.service
        echo 'Stopping old service if running...'
        echo '${PI_PASSWORD}' | sudo -S systemctl stop henry.service 2>/dev/null || true
        echo 'Starting service...'
        echo '${PI_PASSWORD}' | sudo -S systemctl start henry.service
        echo 'Vacuuming old logs...'
        echo '${PI_PASSWORD}' | sudo -S journalctl --vacuum-size=100M --vacuum-time=7d
    "
else
    ssh -t "${PI_USER}@${PI_HOST}" "
        sudo mkdir -p /etc/systemd/journald.conf.d
        sudo mv /tmp/henry-journal.conf /etc/systemd/journald.conf.d/henry.conf
        sudo mv /tmp/henry.service /etc/systemd/system/henry.service
        sudo systemctl daemon-reload
        sudo systemctl restart systemd-journald
        sudo systemctl enable henry.service
        echo 'Stopping old service if running...'
        sudo systemctl stop henry.service 2>/dev/null || true
        echo 'Starting service...'
        sudo systemctl start henry.service
        echo 'Vacuuming old logs...'
        sudo journalctl --vacuum-size=100M --vacuum-time=7d
    "
fi

echo ""
echo "==========================================="
echo "Deployment complete!"
echo "==========================================="
echo ""
echo "Log rotation configured:"
echo "  - Max journal size: 100MB"
echo "  - Max retention: 7 days"
echo "  - Logs auto-pruned to save SSD space"
echo ""
echo "Useful commands:"
echo "  Check status:    ssh ${PI_USER}@${PI_HOST} 'sudo systemctl status henry.service'"
echo "  View logs:       ssh ${PI_USER}@${PI_HOST} 'sudo journalctl -u henry.service -f'"
echo "  View last 50:    ssh ${PI_USER}@${PI_HOST} 'sudo journalctl -u henry.service -n 50'"
echo "  Restart service: ssh ${PI_USER}@${PI_HOST} 'sudo systemctl restart henry.service'"
echo "  Stop service:    ssh ${PI_USER}@${PI_HOST} 'sudo systemctl stop henry.service'"
echo "  Clean logs now:  ssh ${PI_USER}@${PI_HOST} 'sudo journalctl --vacuum-size=50M'"
echo "  Check disk:      ssh ${PI_USER}@${PI_HOST} 'df -h'"
echo ""
echo "Make sure your server is running before starting the Pi service!"
echo ""


