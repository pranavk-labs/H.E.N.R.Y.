#!/bin/bash
# Deployment script for Raspberry Pi

set -e

# Configuration
PI_USER="${PI_USER:-pi}"
PI_HOST="${PI_HOST:-raspberrypi.local}"
PI_PATH="${PI_PATH:-/home/pi/H.E.N.R.Y.}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Deploying H.E.N.R.Y. to Raspberry Pi..."
echo "Target: ${PI_USER}@${PI_HOST}:${PI_PATH}"

# Check if SSH key is available
if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Warning: No SSH key found. You may need to enter password."
fi

# Create remote directory
echo "Creating remote directory..."
ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${PI_PATH}"

# Copy files (excluding unnecessary files)
echo "Copying files..."
rsync -avz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env.local' \
    --exclude='.env' \
    --exclude='data/' \
    --exclude='*.db' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='venv/' \
    --exclude='.venv/' \
    "${PROJECT_ROOT}/" "${PI_USER}@${PI_HOST}:${PI_PATH}/"

# Install dependencies on Pi
echo "Installing dependencies on Pi..."
ssh "${PI_USER}@${PI_HOST}" "cd ${PI_PATH} && poetry install --no-dev"

# Copy .env.pi if it exists
if [ -f "${PROJECT_ROOT}/.env.pi" ]; then
    echo "Copying .env.pi..."
    scp "${PROJECT_ROOT}/.env.pi" "${PI_USER}@${PI_HOST}:${PI_PATH}/.env"
fi

# Restart service if systemd service exists
echo "Restarting service..."
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl restart henry.service || echo 'Service not found, skipping restart'"

echo "Deployment complete!"
echo "To check service status: ssh ${PI_USER}@${PI_HOST} 'sudo systemctl status henry.service'"


