"""Settings"""

import os
from enum import StrEnum

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    PROD = "prod"
    LOCAL = "local"


class Settings(BaseSettings):
    turso_database_url: str = ""
    turso_auth_token: str = ""
    telegram_bot_token: str = ""
    logfire_token: str = ""


def create_settings(env: Env | None = None) -> Settings:
    """Create settings instance with appropriate environment configuration."""

    # Load environment variables from .env file
    load_dotenv()

    # Read the 'environment' variable
    environment = os.environ.get("ENVIRONMENT", env)

    # Raise an error if the environment is not valid
    assert environment is not None, "Environment not set"
    assert environment in Env, f"Invalid environment: {environment}"

    # Build the settings configuration based on the environment
    config = SettingsConfigDict(
        env_prefix=f"{environment.upper()}_",
        env_file=".env",
        ignore_empty_file=True,
        extra="ignore",
    )

    # Create a new settings class with the configuration
    class ConfiguredSettings(Settings):
        model_config = config

    # Return an instance of the configured settings
    return ConfiguredSettings()
