# H.E.N.R.Y. Server Dockerfile
# This container runs the API server with OpenAI Whisper STT support

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies (including whisper for server)
RUN poetry config virtualenvs.create false &&\ 
    poetry lock --no-interaction --no-ansi &&\
    poetry install --no-interaction --no-ansi --extras server --without dev --no-root

# Copy application code
COPY backend/ ./backend/
COPY tools/ ./tools/

# Copy .env.server as .env inside the container
# Docker Compose also injects these vars via env_file, this just makes the file visible
COPY .env.server .env

# Create directory for Whisper model cache
RUN mkdir -p /root/.cache/whisper

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API server
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
