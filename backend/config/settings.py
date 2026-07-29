"""Environment configuration management using Pydantic Settings."""

import logging
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
    ollama_keep_alive: str = Field(default="5m", alias="OLLAMA_KEEP_ALIVE")
    ollama_unload_on_stop: bool = Field(
        default=True, alias="OLLAMA_UNLOAD_ON_STOP"
    )

    # Audio / Voice Configuration
    audio_enabled: bool = Field(default=False, alias="AUDIO_ENABLED")
    wake_word: str = Field(default="Hey HENRY", alias="WAKE_WORD")

    # Voice Runtime Configuration
    voice_runtime: str = Field(default="legacy", alias="VOICE_RUNTIME")
    voice_runtime_url: str = Field(
        default="ws://127.0.0.1:8765/v1/realtime", alias="VOICE_RUNTIME_URL"
    )
    voice_runtime_command: str = Field(default="", alias="VOICE_RUNTIME_COMMAND")
    voice_runtime_device: str = Field(default="cuda", alias="VOICE_RUNTIME_DEVICE")
    voice_runtime_auto_start: bool = Field(
        default=False, alias="VOICE_RUNTIME_AUTO_START"
    )
    voice_runtime_llm_model: str = Field(
        default="", alias="VOICE_RUNTIME_LLM_MODEL"
    )

    # STT Configuration (Speech-to-Text)
    # Options: "none" (raise if called), "dummy" (return empty string), "whisper" (server-side, requires openai-whisper), "remote" (send to server)
    stt_engine: str = Field(default="none", alias="STT_ENGINE")
    # Whisper model size: "tiny" (fastest, lowest accuracy), "base" (balanced), "small", "medium", "large" (best accuracy, slowest)
    # For server, recommend "small" for better accuracy
    whisper_model_size: str = Field(
        default="small", alias="WHISPER_MODEL_SIZE"
    )
    # STT server URL for remote transcription (Pi sends audio to this server)
    stt_server_url: str = Field(default="", alias="STT_SERVER_URL")

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

    # GUI Display Configuration
    fullscreen: bool = Field(default=False, alias="FULLSCREEN")  # Enable fullscreen mode (True for Pi)

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
        # Get current working directory for debugging
        cwd = os.getcwd()
        print(f"DEBUG: Current working directory: {cwd}")

        # Determine which .env file to load based on APP_ENV
        app_env = os.getenv("APP_ENV", "development")
        print(f"DEBUG: APP_ENV = {app_env}")

        # Try different .env files in order of preference
        if app_env == "production":
            # Production (Pi): try .env, .env.pi, then .env.local
            env_files = [".env", ".env.pi", ".env.server", ".env.local"]
        else:
            # Development: try .env.local, .env, .env.pi (also check .env.pi for dev)
            env_files = [".env.local", ".env", ".env.pi"]

        # Debug: Check which files exist
        print("DEBUG: Checking for environment files:")
        for env_file in env_files:
            abs_path = os.path.abspath(env_file)
            exists = os.path.exists(env_file)
            print(f"  - {env_file} -> {abs_path} [{'EXISTS' if exists else 'NOT FOUND'}]")

        # Find first existing file and load it explicitly with dotenv
        env_file_to_use = None
        for env_file in env_files:
            if os.path.exists(env_file):
                env_file_to_use = env_file
                abs_path = os.path.abspath(env_file)
                # Explicitly load environment variables from the file
                # This ensures API_BASE_URL and other vars are in os.environ
                result = load_dotenv(env_file, override=False)
                msg = f"Loaded environment from {env_file_to_use} (full path: {abs_path}, APP_ENV={app_env}, load_dotenv returned: {result})"
                print(msg)  # Print to stdout as backup
                logger.info(msg)
                break

        if env_file_to_use:
            _settings = Settings(_env_file=env_file_to_use)
        else:
            # No .env file found, use defaults
            msg = f"No .env file found (tried: {', '.join(env_files)}), using defaults (APP_ENV={app_env})"
            print(f"WARNING: {msg}")  # Print to stdout as backup
            logger.warning(msg)
            _settings = Settings()

        # Log important configuration
        api_base_url = os.getenv("API_BASE_URL")
        if api_base_url:
            msg = f"API_BASE_URL configured: {api_base_url}"
            print(msg)  # Print to stdout as backup
            logger.info(msg)
        else:
            msg = "API_BASE_URL not set (will use direct service calls)"
            print(msg)  # Print to stdout as backup
            logger.info(msg)

    return _settings
