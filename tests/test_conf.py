from pathlib import Path
from typing import Generator

import pytest

from src.conf import Env, create_settings


@pytest.fixture
def mock_env_files(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary .env and .env.sample files with test configuration."""

    # Main .env file
    env_content = """
# Local settings
LOCAL_TURSO_DATABASE_URL=file:local.db
LOCAL_TURSO_AUTH_TOKEN=local-token

# Prod settings
PROD_TURSO_DATABASE_URL=https://prod.db
PROD_TURSO_AUTH_TOKEN=prod-token
""".strip()

    # Create both files
    env_file = tmp_path / ".env"
    env_file.write_text(env_content)
    yield env_file

    # Cleanup
    env_file.unlink(missing_ok=True)


@pytest.fixture
def _mock_env(mock_env_files: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup environment for testing."""
    monkeypatch.chdir(mock_env_files.parent)


@pytest.mark.usefixtures("_mock_env")
def test_create_settings_local() -> None:
    """Test local environment settings."""
    settings = create_settings(env=Env.LOCAL)

    assert settings.turso_database_url == "file:local.db"
    assert settings.turso_auth_token == "local-token"


@pytest.mark.usefixtures("_mock_env")
def test_create_settings_prod() -> None:
    """Test production environment settings."""
    settings = create_settings(env=Env.PROD)

    assert settings.turso_database_url == "https://prod.db"
    assert settings.turso_auth_token == "prod-token"


def test_create_settings_no_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test settings with missing .env file falls back to defaults."""
    # Change to an empty directory
    monkeypatch.chdir(tmp_path)

    settings = create_settings(env=Env.LOCAL)

    # Should use default values from Settings class
    assert settings.turso_database_url == ""
    assert settings.turso_auth_token == ""
