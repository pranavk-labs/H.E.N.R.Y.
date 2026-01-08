# Local Development Guide

## Overview

This guide covers developing H.E.N.R.Y. on your local machine and deploying to the Raspberry Pi. The recommended workflow is to develop and test locally, then deploy to Pi for hardware-specific testing and production use.

## Quick Start

### 1. Local Setup

```bash
# Clone repository
git clone <repository-url>
cd H.E.N.R.Y.

# Install Poetry (if not already installed)
# macOS/Linux: curl -sSL https://install.python-poetry.org | python3 -
# Windows: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Install dependencies (Poetry creates virtual environment automatically)
poetry install

# Activate Poetry shell (optional, or use 'poetry run' prefix)
poetry shell

# Create local environment file
cp .env.example .env.local

# Edit .env.local with your configuration
# Option 1: Connect to home server services
# Option 2: Use local services (Neo4j, Ollama)
```

### 2. Configure Environment

**`.env.local`** - For local development:

```env
# Application
APP_ENV=development
DEBUG=True

# Services - Connect to home server (recommended)
NEO4J_URI=bolt://home-server-tailscale-ip:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

OLLAMA_BASE_URL=http://home-server-tailscale-ip:11434

# Or use local services
# NEO4J_URI=bolt://localhost:7687
# OLLAMA_BASE_URL=http://localhost:11434

# Disable hardware features locally
AUDIO_ENABLED=False
ROBOT_ENABLED=False

# API
API_HOST=127.0.0.1
API_PORT=8000
```

### 3. Run Development Server

```bash
# Load environment and run with Poetry
export $(cat .env.local | xargs)  # Linux/macOS
poetry run python scripts/dev_server.py

# Or directly with uvicorn
poetry run uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000

# If using poetry shell, you can run commands directly
poetry shell
python scripts/dev_server.py
```

## Service Options

### Option 1: Connect to Home Server (Recommended)

**Advantages:**

-   No need to run services locally
-   Tests real network connectivity
-   Uses production-like setup
-   No resource usage on local machine

**Setup:**

1. Install Tailscale on local machine
2. Connect to same Tailscale network as Pi and home server
3. Get home server Tailscale IP
4. Configure `.env.local` with home server addresses

### Option 2: Run Services Locally

**Advantages:**

-   Works offline
-   Faster (no network latency)
-   Full control over services

**Setup Neo4j:**

```bash
# Using Docker
docker run -d \
    --name neo4j-dev \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/devpassword \
    -v neo4j_data:/data \
    neo4j:latest

# Access at http://localhost:7474
```

**Setup Ollama:**

```bash
# Install Ollama (https://ollama.ai)
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.2:3b
```

### Option 3: Mock Services (For Testing)

Use mocks for unit tests and rapid development:

```python
# tests/mocks/neo4j_mock.py
class MockNeo4jClient:
    def execute_query(self, query, params=None):
        # Return mock data
        return []
```

## Deployment to Raspberry Pi

### Method 1: Git-Based (Recommended)

**On Pi:**

```bash
cd ~/H.E.N.R.Y.
git pull origin main
poetry install  # Updates dependencies if pyproject.toml changed
sudo systemctl restart henry.service
```

**Workflow:**

1. Develop and test locally
2. Commit and push to Git
3. SSH to Pi and pull changes
4. Restart service

### Method 2: Rsync Deployment

**Create `scripts/deploy.sh`:**

```bash
#!/bin/bash

PI_USER="pi"
PI_HOST="raspberry-pi-ip"  # or Tailscale IP
PI_PATH="~/H.E.N.R.Y."

# Sync files
rsync -avz --delete \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.env.local' \
    --exclude 'poetry.lock' \
    ./ ${PI_USER}@${PI_HOST}:${PI_PATH}/

# Deploy on Pi
ssh ${PI_USER}@${PI_HOST} << 'ENDSSH'
cd ~/H.E.N.R.Y.
poetry install  # Updates dependencies if pyproject.toml changed
sudo systemctl restart henry.service
ENDSSH
```

**Usage:**

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Method 3: VS Code Remote Development

1. Install "Remote - SSH" extension in VS Code
2. Connect to Pi via SSH
3. Open project folder on Pi
4. Develop directly on Pi (slower but good for debugging)

## Testing Strategy

### Local Testing

**Unit Tests:**

```bash
# Run with mocks
pytest tests/unit/ -v
```

**Integration Tests:**

```bash
# Run with local services or home server
pytest tests/integration/ -v
```

**API Testing:**

```bash
# Start dev server
poetry run python scripts/dev_server.py

# In another terminal
curl http://localhost:8000/api/v1/health
```

### Pi Testing

**When to Test on Pi:**

-   Audio/voice features
-   GPIO/robot control
-   Performance under Pi constraints
-   Final integration testing

**Deploy and Test:**

```bash
# Deploy to Pi
./scripts/deploy.sh

# SSH to Pi and check logs
ssh pi@raspberry-pi-ip
sudo journalctl -u henry.service -f
```

## Environment Management

### Multiple Environments

Use different `.env` files for different environments:

-   `.env.local` - Local development
-   `.env.pi` - Raspberry Pi
-   `.env.example` - Template

### Environment Detection

```python
# backend/config/settings.py
from pathlib import Path
import os

def get_env_file():
    """Auto-detect environment file"""
    if os.getenv('APP_ENV') == 'production':
        return '.env.pi'
    elif Path('.env.local').exists():
        return '.env.local'
    else:
        return '.env'

class Settings(BaseSettings):
    # ... settings ...

    class Config:
        env_file = get_env_file()
```

## Common Workflows

### Daily Development

1. **Start local services** (if using local):

    ```bash
    docker start neo4j-dev
    ollama serve
    ```

2. **Run development server**:

```bash
poetry run python scripts/dev_server.py
# or if in poetry shell:
python scripts/dev_server.py
```

3. **Make changes and test locally**

4. **Run tests**:

```bash
poetry run pytest
# or if in poetry shell:
pytest
```

5. **Commit and push**:
    ```bash
    git add .
    git commit -m "feat: add new feature"
    git push
    ```

### Deploy to Pi

1. **Deploy**:

    ```bash
    ./scripts/deploy.sh
    ```

2. **Test on Pi**:

    ```bash
    ssh pi@raspberry-pi-ip
    curl http://localhost:8000/api/v1/health
    ```

3. **Check logs**:
    ```bash
    sudo journalctl -u henry.service -f
    ```

## Troubleshooting

### Connection Issues

**Can't connect to home server:**

-   Check Tailscale is running: `tailscale status`
-   Verify home server is online
-   Check firewall settings
-   Test connectivity: `ping home-server-ip`

### Local Services Not Working

**Neo4j:**

-   Check Docker is running: `docker ps`
-   Verify port 7687 is available
-   Check logs: `docker logs neo4j-dev`

**Ollama:**

-   Check Ollama is running: `ollama list`
-   Verify port 11434 is available
-   Check logs: `ollama serve` (run in foreground)

### Deployment Issues

**Rsync fails:**

-   Check SSH access: `ssh pi@raspberry-pi-ip`
-   Verify Pi path exists
-   Check permissions

**Service won't start on Pi:**

-   Check logs: `sudo journalctl -u henry.service`
-   Verify environment file exists: `.env.pi`
-   Check service file: `sudo systemctl status henry.service`

## Best Practices

1. **Develop Locally**: Write and test code on local machine
2. **Use Home Server Services**: Connect to real services for integration testing
3. **Mock for Unit Tests**: Use mocks for fast unit tests
4. **Deploy Regularly**: Test on Pi periodically, not just at the end
5. **Version Control**: Use Git for all code, deploy via Git or rsync
6. **Environment Files**: Never commit `.env` files, use `.env.example`
7. **Documentation**: Update docs when changing deployment process
