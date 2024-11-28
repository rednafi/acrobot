import logging
from typing import Any
from unittest.mock import AsyncMock, mock_open, patch

from libsql_client import Client

from src.db import get_db_client, init_db


async def test_init_db() -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch("libsql_client.create_client", return_value=mock_client),
        patch("builtins.open", mock_open(read_data="CREATE TABLE test;")),
        patch("sqlparse.split", return_value=["CREATE TABLE test;"]),
    ):
        await init_db("mock_url", "mock_token", "mock_sql_dir")

        mock_client.execute.assert_awaited_once_with("CREATE TABLE test;")


async def test_get_db_client() -> None:
    mock_client = AsyncMock(spec=Client)

    # Mock the return value of create_client to be mock_client
    with (
        patch(
            "libsql_client.create_client", return_value=mock_client
        ) as mock_create_client,
        patch("src.db.settings") as mock_settings,
    ):
        mock_settings.turso_database_url = "mock_url"
        mock_settings.turso_auth_token = "mock_token"

        result: Client = await get_db_client()

        # Ensure create_client was called with the correct arguments
        mock_create_client.assert_called_once_with("mock_url", auth_token="mock_token")

        # Verify that the result is the mocked client
        assert result is mock_client


def test_logs(caplog: Any) -> None:
    with caplog.at_level(logging.INFO):
        logger = logging.getLogger("acrobot.db")
        logger.info("Database initialized...")
    assert "Database initialized..." in caplog.text
