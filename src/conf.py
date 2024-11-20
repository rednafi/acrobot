from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    PROD = "prod"
    LOCAL = "local"


class Settings(BaseSettings):
    turso_database_url: str = ""
    turso_auth_token: str = ""


def create_settings(env: Env) -> Settings:
    """Create settings instance with appropriate environment configuration."""

    config = SettingsConfigDict(
        env_prefix=f"{env.value.upper()}_",
        env_file=".env",
        ignore_empty_file=True,
        extra="ignore",
    )

    # Create a new class that inherits from Settings
    class ConfiguredSettings(Settings):
        model_config = config

    return ConfiguredSettings()


if __name__ == "__main__":
    settings = create_settings(env=Env.PROD)
    print(settings.turso_database_url)
    print(settings.turso_auth_token)
