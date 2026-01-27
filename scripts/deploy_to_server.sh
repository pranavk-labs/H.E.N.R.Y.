#!/bin/bash
# Deployment script for H.E.N.R.Y. Server (Docker)

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load configuration from .env.deploy if it exists
if [ -f "${PROJECT_ROOT}/.env.deploy" ]; then
    echo "Loading configuration from .env.deploy..."
    set -a
    source "${PROJECT_ROOT}/.env.deploy"
    set +a
fi

# Configuration (with defaults)
SERVER_USER="${SERVER_USER:-$(whoami)}"
SERVER_HOST="${SERVER_HOST:-localhost}"
SERVER_PATH="${SERVER_PATH:-/home/${SERVER_USER}/H.E.N.R.Y.}"
SERVER_PASSWORD="${SERVER_PASSWORD:-}"

# Check if sshpass is available for password automation
if [ -n "$SERVER_PASSWORD" ] && ! command -v sshpass &> /dev/null; then
    echo "Warning: SERVER_PASSWORD set but sshpass not installed."
    echo "Install with: sudo apt install sshpass  (or brew install hudochenkov/sshpass/sshpass on macOS)"
    echo "Falling back to interactive password prompts."
    SERVER_PASSWORD=""
fi

echo "==========================================="
echo "H.E.N.R.Y. Server Deployment (Docker)"
echo "==========================================="
echo "Target: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}"
echo ""

# Check if deploying to remote or local
if [ "$SERVER_HOST" = "localhost" ] || [ "$SERVER_HOST" = "127.0.0.1" ]; then
    DEPLOY_MODE="local"
    echo "Deployment mode: LOCAL"
else
    DEPLOY_MODE="remote"
    echo "Deployment mode: REMOTE"

    # Check if SSH key is available
    if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
        echo "Warning: No SSH key found. You may need to enter password."
    fi
fi

# Function to run commands locally or via SSH
run_command() {
    if [ "$DEPLOY_MODE" = "local" ]; then
        eval "$1"
    else
        if [ -n "$SERVER_PASSWORD" ]; then
            sshpass -p "$SERVER_PASSWORD" ssh -t "${SERVER_USER}@${SERVER_HOST}" "$1"
        else
            ssh -t "${SERVER_USER}@${SERVER_HOST}" "$1"
        fi
    fi
}

# Function to copy files locally or via rsync
copy_files() {
    if [ "$DEPLOY_MODE" = "local" ]; then
        mkdir -p "$2"
        rsync -a --delete \
            --exclude='.git' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.env.local' \
            --exclude='.env.pi' \
            --exclude='data/' \
            --exclude='*.db' \
            --exclude='.pytest_cache' \
            --exclude='.mypy_cache' \
            --exclude='venv/' \
            --exclude='.venv/' \
            --exclude='poetry.lock' \
            "$1/" "$2/"
    else
        if [ -n "$SERVER_PASSWORD" ]; then
            sshpass -p "$SERVER_PASSWORD" rsync -avz \
                --exclude='.git' \
                --exclude='__pycache__' \
                --exclude='*.pyc' \
                --exclude='.env.local' \
                --exclude='.env.pi' \
                --exclude='data/' \
                --exclude='*.db' \
                --exclude='.pytest_cache' \
                --exclude='.mypy_cache' \
                --exclude='venv/' \
                --exclude='.venv/' \
                --exclude='poetry.lock' \
                "$1/" "${SERVER_USER}@${SERVER_HOST}:$2/"
        else
            rsync -avz \
                --exclude='.git' \
                --exclude='__pycache__' \
                --exclude='*.pyc' \
                --exclude='.env.local' \
                --exclude='.env.pi' \
                --exclude='data/' \
                --exclude='*.db' \
                --exclude='.pytest_cache' \
                --exclude='.mypy_cache' \
                --exclude='venv/' \
                --exclude='.venv/' \
                --exclude='poetry.lock' \
                "$1/" "${SERVER_USER}@${SERVER_HOST}:$2/"
        fi
    fi
}

# Create remote directory
echo "Creating server directory..."
run_command "mkdir -p ${SERVER_PATH}"

# Copy files
echo "Copying files..."
copy_files "${PROJECT_ROOT}" "${SERVER_PATH}"

# Copy .env.server if it exists
if [ -f "${PROJECT_ROOT}/.env.server" ]; then
    echo "Copying .env.server..."
    if [ "$DEPLOY_MODE" = "local" ]; then
        cp "${PROJECT_ROOT}/.env.server" "${SERVER_PATH}/.env.server"
    else
        if [ -n "$SERVER_PASSWORD" ]; then
            sshpass -p "$SERVER_PASSWORD" scp "${PROJECT_ROOT}/.env.server" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/.env.server"
        else
            scp "${PROJECT_ROOT}/.env.server" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/.env.server"
        fi
    fi
else
    echo "Warning: .env.server not found. You'll need to create it on the server."
fi

# Check if Docker is installed
echo "Checking Docker installation..."
if ! run_command "command -v docker &> /dev/null"; then
    echo "Error: Docker is not installed on the server."
    echo "Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

# Determine docker-compose command (standalone or plugin)
if run_command "command -v docker-compose &> /dev/null"; then
    DOCKER_COMPOSE_CMD="sudo docker-compose"
else
    echo "docker-compose not found, using 'docker compose' plugin."
    DOCKER_COMPOSE_CMD="sudo docker compose"
fi

# Stop and clean up old containers
echo "Stopping old containers..."
if [ "$DEPLOY_MODE" = "local" ]; then
    cd "${SERVER_PATH}"
    ${DOCKER_COMPOSE_CMD} down || true
else
    if [ -n "$SERVER_PASSWORD" ]; then
        sshpass -p "$SERVER_PASSWORD" ssh -t "${SERVER_USER}@${SERVER_HOST}" "
            cd ${SERVER_PATH} 2>/dev/null && echo '${SERVER_PASSWORD}' | sudo -S ${DOCKER_COMPOSE_CMD#sudo } down || true
        "
    else
        ssh -t "${SERVER_USER}@${SERVER_HOST}" "
            cd ${SERVER_PATH} 2>/dev/null && ${DOCKER_COMPOSE_CMD} down || true
        "
    fi
fi

# Clean up dangling images and unused resources
echo "Cleaning up unused Docker resources..."
if [ "$DEPLOY_MODE" = "local" ]; then
    sudo docker image prune -f
    sudo docker volume prune -f
else
    if [ -n "$SERVER_PASSWORD" ]; then
        sshpass -p "$SERVER_PASSWORD" ssh -t "${SERVER_USER}@${SERVER_HOST}" "
            echo '${SERVER_PASSWORD}' | sudo -S docker image prune -f
            echo '${SERVER_PASSWORD}' | sudo -S docker volume prune -f
        "
    else
        ssh -t "${SERVER_USER}@${SERVER_HOST}" "
            sudo docker image prune -f
            sudo docker volume prune -f
        "
    fi
fi

# Build and start Docker containers (all in one SSH session)
echo "Building and starting Docker containers..."
if [ "$DEPLOY_MODE" = "local" ]; then
    cd "${SERVER_PATH}"
    ${DOCKER_COMPOSE_CMD} build
    ${DOCKER_COMPOSE_CMD} up -d
    sleep 5
    ${DOCKER_COMPOSE_CMD} ps
    echo ""
    echo "Recent logs:"
    ${DOCKER_COMPOSE_CMD} logs --tail=20
else
    # Run all docker commands in a single SSH session with sudo
    if [ -n "$SERVER_PASSWORD" ]; then
        sshpass -p "$SERVER_PASSWORD" ssh -t "${SERVER_USER}@${SERVER_HOST}" "
            cd ${SERVER_PATH}
            echo 'Building Docker image...'
            echo '${SERVER_PASSWORD}' | sudo -S ${DOCKER_COMPOSE_CMD#sudo } build

            echo 'Starting Docker containers...'
            echo '${SERVER_PASSWORD}' | sudo -S ${DOCKER_COMPOSE_CMD#sudo } up -d

            echo 'Waiting for container to be healthy...'
            sleep 5

            echo 'Checking container status...'
            echo '${SERVER_PASSWORD}' | sudo -S ${DOCKER_COMPOSE_CMD#sudo } ps

            echo ''
            echo 'Recent logs:'
            echo '${SERVER_PASSWORD}' | sudo -S ${DOCKER_COMPOSE_CMD#sudo } logs --tail=20
        "
    else
        ssh -t "${SERVER_USER}@${SERVER_HOST}" "
            cd ${SERVER_PATH}
            echo 'Building Docker image...'
            ${DOCKER_COMPOSE_CMD} build

            echo 'Starting Docker containers...'
            ${DOCKER_COMPOSE_CMD} up -d

            echo 'Waiting for container to be healthy...'
            sleep 5

            echo 'Checking container status...'
            ${DOCKER_COMPOSE_CMD} ps

            echo ''
            echo 'Recent logs:'
            ${DOCKER_COMPOSE_CMD} logs --tail=20
        "
    fi
fi

echo ""
echo "==========================================="
echo "Deployment complete!"
echo "==========================================="
echo ""
echo "Useful commands:"
if [ "$DEPLOY_MODE" = "remote" ]; then
    echo "  View logs:       ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && sudo docker compose logs -f'"
    echo "  Restart:         ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && sudo docker compose restart'"
    echo "  Stop:            ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && sudo docker compose down'"
    echo "  Rebuild:         ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && sudo docker compose up -d --build'"
    echo "  Container shell: ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && sudo docker compose exec henry-server bash'"
    echo "  Check status:    ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && sudo docker compose ps'"
else
    echo "  View logs:       cd ${SERVER_PATH} && sudo docker compose logs -f"
    echo "  Restart:         cd ${SERVER_PATH} && sudo docker compose restart"
    echo "  Stop:            cd ${SERVER_PATH} && sudo docker compose down"
    echo "  Rebuild:         cd ${SERVER_PATH} && sudo docker compose up -d --build"
    echo "  Container shell: cd ${SERVER_PATH} && sudo docker compose exec henry-server bash"
    echo "  Check status:    cd ${SERVER_PATH} && sudo docker compose ps"
fi
echo ""
