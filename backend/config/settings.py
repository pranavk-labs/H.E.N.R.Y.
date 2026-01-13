"""Environment configuration management using Pydantic Settings."""

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,  # Allow both field names and aliases
    )

    # Application
    app_env: Literal["development", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    debug: bool = Field(default=True, alias="DEBUG")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="", alias="NEO4J_PASSWORD")

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL"
    )

    # Audio / Voice Configuration
    audio_enabled: bool = Field(default=False, alias="AUDIO_ENABLED")
    wake_word: str = Field(default="Hey HENRY", alias="WAKE_WORD")

    # STT Configuration (Speech-to-Text)
    # Options: "none" (raise if called), "dummy" (return empty string), "whisper" (free, open-source, offline)
    stt_engine: str = Field(default="none", alias="STT_ENGINE")
    # Whisper model size: "tiny" (fastest, lowest accuracy), "base" (balanced), "small", "medium", "large" (best accuracy, slowest)
    # For Raspberry Pi, recommend "tiny" or "base" for speed, "small" for better accuracy
    whisper_model_size: str = Field(
        default="base", alias="WHISPER_MODEL_SIZE"
    )

    # TTS Configuration (Text-to-Speech)
    # Options: "log" (just logs), "piper" (default, neural TTS, natural, offline), "pyttsx3" (free, offline, uses system voices)
    tts_engine: str = Field(default="piper", alias="TTS_ENGINE")
    tts_rate: int = Field(default=175, alias="TTS_RATE")  # Speech rate (words per minute) - for pyttsx3 only
    tts_volume: float = Field(default=1.0, alias="TTS_VOLUME")  # Volume (0.0 to 1.0) - for pyttsx3 only
    # Voice selection
    # For Piper: voice model name (e.g., "en_US-lessac-medium") or leave empty for default
    # For pyttsx3: voice name/ID (e.g., "en-us", "mb-en1" for MBROLA)
    tts_voice: str = Field(default="", alias="TTS_VOICE")
    # Piper TTS model path (full path to .onnx file) - if empty, auto-detects from voice name
    tts_piper_model_path: str = Field(default="", alias="TTS_PIPER_MODEL_PATH")
    # Pitch adjustment (0-100, default 50) - only for pyttsx3 on some platforms
    tts_pitch: int = Field(default=50, alias="TTS_PITCH")

    # GUI Personality Configuration - Emotional state timing (in seconds)
    # Time thresholds for transitioning between emotional states based on inactivity
    gui_happy_duration: int = Field(default=120, alias="GUI_HAPPY_DURATION")  # Happy state (0-120s, default 2 min)
    gui_neutral_duration: int = Field(default=300, alias="GUI_NEUTRAL_DURATION")  # Neutral state (120-300s, default 5 min)
    gui_sleepy_duration: int = Field(default=600, alias="GUI_SLEEPY_DURATION")  # Sleepy state (300-600s, default 10 min)
    # After sleepy_duration, HENRY becomes "very sleepy" (asleep)

    # Voice Loop Configuration
    wake_word_cooldown: float = Field(default=3.0, alias="WAKE_WORD_COOLDOWN")  # Seconds to debounce wake word (prevent multiple triggers)

    def get_env_file(self) -> str:
        """Get the appropriate .env file based on environment."""
        if self.app_env == "production":
            return ".env.pi"
        return ".env.local"


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        # Try to load from .env.local first, then .env.pi
        env_file = os.getenv("APP_ENV", "development")
        if env_file == "production":
            _settings = Settings(_env_file=".env.pi")
        else:
            _settings = Settings(_env_file=".env.local")
    return _settings

