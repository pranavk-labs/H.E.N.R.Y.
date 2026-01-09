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

    # Audio Configuration
    audio_enabled: bool = Field(default=False, alias="AUDIO_ENABLED")
    wake_word: str = Field(default="Hey HENRY", alias="WAKE_WORD")

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

