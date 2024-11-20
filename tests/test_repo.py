import os
from collections.abc import AsyncGenerator

import libsql_client
import pytest

from src.repo import SqliteRepository


@pytest.fixture
async def db_client() -> AsyncGenerator[libsql_client.Client, None]:
    """Fixture to create a test SQLite client."""
    async with libsql_client.create_client("file:test.db") as client:
        with open("sql/ddl.sql") as f:
            ddl = f.read()

        os.remove("test.db")
        await client.execute(ddl)
        yield client
        os.remove("test.db")


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
        success = await repo.add("key1", ["value1", "value2"])
        assert success, "Add operation should be successful."

        result = await repo.get("key1")
        assert result == [
            "value1",
            "value2",
        ], "Add and Get should work and return sorted unique values."

    async def test_add_with_duplicates(self, repo: SqliteRepository) -> None:
        """Test adding duplicate values."""
        success1 = await repo.add("key1", ["value1", "value2"])
        assert success1, "Initial Add operation should be successful."

        success2 = await repo.add("key1", ["value2", "value3"])
        assert success2, "Add operation with duplicates should be successful."

        result = await repo.get("key1")
        assert result == [
            "value1",
            "value2",
            "value3",
        ], "Duplicate values should not be stored."

    async def test_remove_values(self, repo: SqliteRepository) -> None:
        """Test removing specific values."""
        await repo.add("key1", ["value1", "value2", "value3"])
        success = await repo.remove("key1", ["value2"])
        assert success, "Remove operation should be successful."

        result = await repo.get("key1")
        assert result == ["value1", "value3"], "Values should be removed correctly."

    async def test_remove_nonexistent_values(self, repo: SqliteRepository) -> None:
        """Test removing values that don't exist."""
        await repo.add("key1", ["value1", "value2"])
        success = await repo.remove("key1", ["value3"])
        assert (
            not success
        ), "Remove operation should be successful even if values don't exist."

        result = await repo.get("key1")
        assert result == [
            "value1",
            "value2",
        ], "Removing nonexistent values should have no effect."

    async def test_list_keys(self, repo: SqliteRepository) -> None:
        """Test listing all keys."""
        await repo.add("key1", ["value1"])
        await repo.add("key2", ["value2"])

        keys = await repo.list_keys()
        assert keys == [
            "key1",
            "key2",
        ], "List keys should return all keys in the database in insertion order."

    async def test_delete_key(self, repo: SqliteRepository) -> None:
        """Test deleting a key."""
        await repo.add("key1", ["value1", "value2"])
        success = await repo.delete("key1")
        assert success, "Delete operation should be successful."

        result = await repo.get("key1")
        assert result == [], "Deleted keys should return an empty list."

        keys = await repo.list_keys()
        assert "key1" not in keys, "Deleted keys should not appear in list_keys."

    async def test_empty_key(self, repo: SqliteRepository) -> None:
        """Test retrieving and removing from a non-existent key."""
        result = await repo.get("non_existent_key")
        assert result == [], "Getting a non-existent key should return an empty list."

        success_remove = await repo.remove("non_existent_key", ["value"])
        assert (
            not success_remove
        ), "Remove operation should fail for a non-existent key."

        success_delete = await repo.delete("non_existent_key")
        assert (
            not success_delete
        ), "Delete operation should fail for a non-existent key."

        result = await repo.get("non_existent_key")
        assert result == [], "Removing from a non-existent key should have no effect."

    async def test_context_management(self, db_client: libsql_client.Client) -> None:
        """Test proper context management."""
        async with SqliteRepository(db_client=db_client) as repo:
            assert (
                repo._client is not None
            ), "Client should be initialized in __aenter__."

        # Ensure the client is closed
        assert db_client.closed, "Client should be properly closed in __aexit__."
