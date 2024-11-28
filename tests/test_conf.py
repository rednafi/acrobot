from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.conf import Env, Settings, create_settings


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """Fixture to mock environment variables."""
    env_vars = {
        "ENVIRONMENT": "local",
        "LOCAL_TURSO_DATABASE_URL": "mock_local_database_url",
        "LOCAL_TURSO_AUTH_TOKEN": "mock_local_auth_token",
        "LOCAL_TELEGRAM_BOT_TOKEN": "mock_local_telegram_token",
        "LOCAL_LOGFIRE_TOKEN": "mock_local_logfire_token",
    }
    with patch.dict("os.environ", env_vars, clear=True):
        yield env_vars


@pytest.fixture
def mock_dotenv() -> Generator[MagicMock, None, None]:
    """Fixture to mock load_dotenv."""
    with patch("src.conf.load_dotenv", MagicMock()) as mock:
        yield mock


@pytest.mark.usefixtures("mock_dotenv")
def test_create_settings_valid_env(mock_env_vars: dict[str, str]) -> None:
    """Test creating settings with a valid environment."""
    settings = create_settings()
    assert isinstance(settings, Settings)
    assert settings.turso_database_url == mock_env_vars["LOCAL_TURSO_DATABASE_URL"]
    assert settings.turso_auth_token == mock_env_vars["LOCAL_TURSO_AUTH_TOKEN"]
    assert settings.telegram_bot_token == mock_env_vars["LOCAL_TELEGRAM_BOT_TOKEN"]
    assert settings.logfire_token == mock_env_vars["LOCAL_LOGFIRE_TOKEN"]


@pytest.mark.usefixtures("mock_dotenv")
def test_create_settings_invalid_env() -> None:
    """Test creating settings with an invalid environment."""
    with patch.dict("os.environ", {"ENVIRONMENT": "INVALID"}, clear=True):
        with pytest.raises(ValueError, match="Invalid environment: INVALID"):
            create_settings()


@pytest.mark.usefixtures("mock_dotenv")
def test_create_settings_no_env_variable() -> None:
    """Test creating settings without ENVIRONMENT variable."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(AssertionError, match="Environment not set"):
            create_settings()


@pytest.mark.usefixtures("mock_dotenv")
def test_create_settings_invalid_env_variable() -> None:
    """Test creating settings with an invalid ENVIRONMENT variable."""
    with patch.dict("os.environ", {"ENVIRONMENT": "INVALID"}, clear=True):
        with pytest.raises(ValueError, match="Invalid environment: INVALID"):
            create_settings()


@pytest.mark.usefixtures("mock_dotenv")
def test_env_prefix_behavior(mock_env_vars: dict[str, str]) -> None:
    """Test settings loading respects the environment prefix."""
    with patch.dict("os.environ", mock_env_vars, clear=True):
        settings = create_settings(Env.LOCAL)
        assert isinstance(settings, Settings)
        assert settings.turso_database_url == mock_env_vars["LOCAL_TURSO_DATABASE_URL"]
        assert settings.turso_auth_token == mock_env_vars["LOCAL_TURSO_AUTH_TOKEN"]
