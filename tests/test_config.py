"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from backend.config.settings import Settings, get_settings


def test_settings_defaults():
    """Test that settings have correct defaults."""
    # Clear any environment variables that might affect defaults
    env_backup = {}
    for key in ["AUDIO_ENABLED", "APP_ENV", "DEBUG", "API_HOST", "API_PORT", "WAKE_WORD"]:
        env_backup[key] = os.environ.pop(key, None)
    
    try:
        # Create Settings without loading from .env file to test defaults
        settings = Settings(_env_file=None)
        assert settings.app_env == "development"
        assert settings.debug is True
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8000
        assert settings.audio_enabled is False
        assert settings.wake_word == "Hey HENRY"
    finally:
        # Restore environment variables
        for key, value in env_backup.items():
            if value is not None:
                os.environ[key] = value


def test_settings_from_env():
    """Test loading settings from environment variables."""
    os.environ["APP_ENV"] = "production"
    os.environ["DEBUG"] = "False"
    os.environ["API_PORT"] = "9000"
    os.environ["WAKE_WORD"] = "HENRY"

    settings = Settings()
    assert settings.app_env == "production"
    assert settings.debug is False
    assert settings.api_port == 9000
    assert settings.wake_word == "HENRY"

    # Cleanup
    del os.environ["APP_ENV"]
    del os.environ["DEBUG"]
    del os.environ["API_PORT"]
    del os.environ["WAKE_WORD"]


def test_get_settings_singleton():
    """Test that get_settings returns a singleton."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


