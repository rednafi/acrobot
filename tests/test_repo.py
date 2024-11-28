from pathlib import Path
from typing import AsyncGenerator

import libsql_client
import pytest
import sqlparse

from src.repo import AddStatus, DeleteStatus, RemoveStatus, SqliteRepository


@pytest.fixture
async def db_client(tmp_path: Path) -> AsyncGenerator[libsql_client.Client, None]:
    """Fixture to create a test SQLite client."""
    db_path = tmp_path / "test.db"
    db_uri = f"file:{db_path}"

    async with libsql_client.create_client(db_uri) as client:
        # Load the DDL from your SQL schema file
        with open("sql/ddl.sql") as f:
            ddl_content = f.read()

        await client.batch(sqlparse.split(ddl_content))
        yield client


@pytest.fixture
async def repo(
    db_client: libsql_client.Client,
) -> AsyncGenerator[SqliteRepository, None]:
    """Fixture to initialize the SqliteRepository with a real SQLite backend."""
    repository = SqliteRepository(db_client=db_client)
    async with repository:
        yield repository


class TestSqliteRepository:
    """Test suite for SqliteRepository."""

    async def test_add_and_get(self, repo: SqliteRepository) -> None:
        """Test adding and retrieving values."""
        status = await repo.add("key1", ["value1", "value2"])
        assert status == AddStatus.OK

        result = await repo.get("key1")
        assert result == ["value1", "value2"]

    async def test_add_with_duplicates(self, repo: SqliteRepository) -> None:
        """Test adding duplicate values."""
        await repo.add("key1", ["value1", "value2"])
        await repo.add("key1", ["value2", "value3"])

        result = await repo.get("key1")
        assert result == ["value1", "value2", "value3"]

    async def test_remove_values(self, repo: SqliteRepository) -> None:
        """Test removing specific values."""
        await repo.add("key1", ["value1", "value2", "value3"])
        status = await repo.remove("key1", ["value2"])
        assert status == RemoveStatus.OK

        result = await repo.get("key1")
        assert result == ["value1", "value3"]

    async def test_remove_nonexistent_values(self, repo: SqliteRepository) -> None:
        """Test removing values that don't exist."""
        await repo.add("key1", ["value1", "value2"])
        status = await repo.remove("key1", ["value3"])
        assert status == RemoveStatus.NO_VALUES

        result = await repo.get("key1")
        assert result == ["value1", "value2"]

    async def test_list_keys(self, repo: SqliteRepository) -> None:
        """Test listing all keys."""
        await repo.add("key1", ["value1"])
        await repo.add("key2", ["value2"])

        keys = await repo.list_keys()
        assert sorted(keys) == ["key1", "key2"]

    async def test_delete_key(self, repo: SqliteRepository) -> None:
        """Test deleting a key."""
        await repo.add("key1", ["value1", "value2"])
        status = await repo.delete("key1")
        assert status == DeleteStatus.OK

        result = await repo.get("key1")
        assert result == []

        keys = await repo.list_keys()
        assert "key1" not in keys

    async def test_empty_key(self, repo: SqliteRepository) -> None:
        """Test retrieving and removing from a non-existent key."""
        result = await repo.get("non_existent_key")
        assert result == []

        status_remove = await repo.remove("non_existent_key", ["value"])
        assert status_remove == RemoveStatus.NO_KEY

        status_delete = await repo.delete("non_existent_key")
        assert status_delete == DeleteStatus.NO_KEY

    async def test_context_management(self, db_client: libsql_client.Client) -> None:
        """Test proper context management."""
        async with SqliteRepository(db_client=db_client) as repo:
            assert repo._client is not None

        assert db_client.closed
