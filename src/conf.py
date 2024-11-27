"""Settings"""

import os
from enum import StrEnum

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Env(StrEnum):
    PROD = "prod"
    LOCAL = "local"


class Settings(BaseSettings):
    turso_database_url: str = ""
    turso_auth_token: str = ""
    telegram_bot_token: str = ""


def create_settings(env: Env = Env.LOCAL) -> Settings:
    """Create settings instance with appropriate environment configuration."""
    environment: str = os.environ.get("ENVIRONMENT", env)

    assert environment == Env.LOCAL or environment == Env.PROD

    config = SettingsConfigDict(
        env_prefix=f"{environment.upper()}_",
        env_file=".env",
        ignore_empty_file=True,
        extra="ignore",
    )

    class ConfiguredSettings(Settings):
        model_config = config

    return ConfiguredSettings()
