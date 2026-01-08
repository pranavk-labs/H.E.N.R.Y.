# Poetry Setup Guide

## Overview

H.E.N.R.Y. uses Poetry for dependency management. Poetry provides better dependency resolution, lock files, and virtual environment management compared to pip and requirements.txt.

## Installation

### Install Poetry

**macOS/Linux:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Windows (PowerShell):**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

**Verify Installation:**
```bash
poetry --version
```

**Add to PATH (if needed):**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

## Project Setup

### Initialize Poetry Project

If starting from scratch:
```bash
poetry init
```

This will create a `pyproject.toml` file interactively.

### Existing Project

If `pyproject.toml` already exists:
```bash
# Install all dependencies
poetry install

# This creates a virtual environment automatically
# Virtual environment location: ~/.cache/pypoetry/virtualenvs/ (or .venv if configured)
```

## Common Poetry Commands

### Dependency Management

```bash
# Add a new dependency
poetry add fastapi

# Add a development dependency
poetry add --group dev pytest

# Add a dependency with version constraint
poetry add "neo4j>=5.0,<6.0"

# Remove a dependency
poetry remove package-name

# Update all dependencies
poetry update

# Update specific dependency
poetry update package-name

# Show dependency tree
poetry show --tree
```

### Virtual Environment

```bash
# Activate Poetry shell
poetry shell

# Run command in Poetry environment (without activating)
poetry run python script.py
poetry run pytest
poetry run uvicorn backend.api.main:app

# Show virtual environment path
poetry env info

# Remove virtual environment
poetry env remove python
```

### Lock File

```bash
# Update poetry.lock (after changing pyproject.toml)
poetry lock

# Install from lock file (ensures exact versions)
poetry install --no-root
```

## pyproject.toml Structure

Example `pyproject.toml` for H.E.N.R.Y.:

```toml
[tool.poetry]
name = "henry"
version = "0.1.0"
description = "H.E.N.R.Y. - Conversational Desk Assistant"
authors = ["Your Name <you@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
neo4j = "^5.14.0"
openai-whisper = "^20231117"
pyttsx3 = "^2.90"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
httpx = "^0.25.1"
websockets = "^12.0"
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-mock = "^3.12.0"
pytest-cov = "^4.1.0"
black = "^23.11.0"
flake8 = "^6.1.0"
mypy = "^1.7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Development Workflow

### Local Development

```bash
# Install dependencies
poetry install

# Activate shell
poetry shell

# Run development server
python scripts/dev_server.py

# Or run without shell
poetry run python scripts/dev_server.py
```

### Adding New Dependencies

```bash
# Add production dependency
poetry add package-name

# Add development dependency
poetry add --group dev package-name

# Commit both pyproject.toml and poetry.lock
git add pyproject.toml poetry.lock
git commit -m "chore: add package-name dependency"
```

### Deployment

**On Raspberry Pi:**
```bash
cd ~/H.E.N.R.Y.
git pull origin main
poetry install  # Installs/updates dependencies
sudo systemctl restart henry.service
```

## Configuration

### Virtual Environment Location

By default, Poetry creates virtual environments in `~/.cache/pypoetry/virtualenvs/`.

To use `.venv` in project directory:
```bash
poetry config virtualenvs.in-project true
```

### Poetry Configuration

```bash
# Show configuration
poetry config --list

# Set configuration
poetry config virtualenvs.in-project true
poetry config virtualenvs.create true
```

## Troubleshooting

### Virtual Environment Issues

**Problem**: Poetry can't find virtual environment
```bash
# Remove and recreate
poetry env remove python
poetry install
```

**Problem**: Wrong Python version
```bash
# Specify Python version
poetry env use python3.9
poetry install
```

### Dependency Resolution Issues

**Problem**: Dependency conflicts
```bash
# Update lock file
poetry lock --no-update

# Or update all dependencies
poetry update
```

### Installation Issues

**Problem**: Package installation fails
```bash
# Clear cache
poetry cache clear pypi --all

# Try again
poetry install
```

## Migration from requirements.txt

If migrating from requirements.txt:

1. **Create pyproject.toml:**
   ```bash
   poetry init
   ```

2. **Add dependencies:**
   ```bash
   # Read requirements.txt and add each
   poetry add $(cat requirements.txt | grep -v "^#" | cut -d'=' -f1)
   ```

3. **Or manually add to pyproject.toml:**
   ```toml
   [tool.poetry.dependencies]
   fastapi = "^0.104.0"
   # ... etc
   ```

4. **Install:**
   ```bash
   poetry install
   ```

5. **Remove old files:**
   ```bash
   rm requirements.txt
   rm -rf venv/  # If using old venv
   ```

## Best Practices

1. **Always commit poetry.lock**: Ensures reproducible builds
2. **Use version constraints**: Specify compatible versions in pyproject.toml
3. **Separate dev dependencies**: Use `--group dev` for test/lint tools
4. **Update regularly**: Run `poetry update` periodically
5. **Use poetry run**: Prefer `poetry run` over activating shell for scripts
6. **Document dependencies**: Keep pyproject.toml well-organized and commented

## Integration with IDEs

### VS Code

Poetry virtual environments are automatically detected by VS Code Python extension.

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Poetry Environment
3. Select Poetry executable

### Other IDEs

Most IDEs can detect Poetry virtual environments automatically. Check your IDE's Python interpreter settings.

