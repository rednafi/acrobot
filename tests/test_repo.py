import asyncio
import random
from pathlib import Path
from typing import AsyncGenerator

import libsql_client
import pytest
import sqlparse

from src.repo import SqliteRepository, Status


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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
        result = await repo.add("key1", ["value1", "value2"])
        assert result.status == Status.OK

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1", "value2"]

    async def test_add_with_duplicates(self, repo: SqliteRepository) -> None:
        """Test adding duplicate values within the same call and across multiple calls."""
        await repo.add("key1", ["value1", "value2", "value2"])
        await repo.add("key1", ["value2", "value3", "value3"])

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1", "value2", "value3"]

    async def test_add_empty_values(self, repo: SqliteRepository) -> None:
        """Test adding an empty list of values."""
        result = await repo.add("key1", [])
        assert result.status == Status.NO_VALUES

        result = await repo.get("key1")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_add_empty_string_value(self, repo: SqliteRepository) -> None:
        """Test adding values that are empty strings."""
        result = await repo.add("key1", ["", "value1", ""])
        assert result.status == Status.OK

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1"]

    async def test_add_empty_string_key(self, repo: SqliteRepository) -> None:
        """Test adding a key that is an empty string."""
        result = await repo.add("", ["value1"])
        assert result.status == Status.OK

        result = await repo.get("")
        assert result.status == Status.OK
        assert result.data == ["value1"]

    async def test_get_nonexistent_key(self, repo: SqliteRepository) -> None:
        """Test retrieving a key that does not exist."""
        result = await repo.get("non_existent_key")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_get_empty_string_key(self, repo: SqliteRepository) -> None:
        """Test retrieving a key that is an empty string."""
        result = await repo.get("")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_remove_values(self, repo: SqliteRepository) -> None:
        """Test removing specific values."""
        await repo.add("key1", ["value1", "value2", "value3"])
        result = await repo.remove("key1", ["value2"])
        assert result.status == Status.OK

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1", "value3"]

    async def test_remove_empty_values(self, repo: SqliteRepository) -> None:
        """Test removing an empty list of values."""
        await repo.add("key1", ["value1", "value2"])
        result = await repo.remove("key1", [])
        assert result.status == Status.NO_VALUES

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1", "value2"]

    async def test_remove_nonexistent_values(self, repo: SqliteRepository) -> None:
        """Test removing values that don't exist."""
        await repo.add("key1", ["value1", "value2"])
        result = await repo.remove("key1", ["value3"])
        assert result.status == Status.NO_VALUES

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1", "value2"]

    async def test_remove_some_values_not_present(self, repo: SqliteRepository) -> None:
        """Test removing values where some are present and some are not."""
        await repo.add("key1", ["value1", "value2"])
        result = await repo.remove("key1", ["value2", "value3"])
        assert result.status == Status.NO_VALUES

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value1", "value2"]

    async def test_remove_all_values_from_key(self, repo: SqliteRepository) -> None:
        """Test removing all values from a key."""
        await repo.add("key1", ["value1", "value2"])
        result = await repo.remove("key1", ["value1", "value2"])
        assert result.status == Status.OK

        result = await repo.get("key1")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_remove_empty_string_key(self, repo: SqliteRepository) -> None:
        """Test removing values from a key that is an empty string."""
        await repo.add("", ["value1"])
        result = await repo.remove("", ["value1"])
        assert result.status == Status.OK

        result = await repo.get("")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_delete_key(self, repo: SqliteRepository) -> None:
        """Test deleting a key."""
        await repo.add("key1", ["value1", "value2"])
        result = await repo.delete("key1")
        assert result.status == Status.OK

        result = await repo.get("key1")
        assert result.status == Status.NO_KEY
        assert result.data == []

        result = await repo.list_keys()
        assert "key1" not in result.data

    async def test_delete_nonexistent_key(self, repo: SqliteRepository) -> None:
        """Test deleting a key that does not exist."""
        result = await repo.delete("non_existent_key")
        assert result.status == Status.NO_KEY

    async def test_delete_empty_string_key(self, repo: SqliteRepository) -> None:
        """Test deleting a key that is an empty string."""
        await repo.add("", ["value1"])
        result = await repo.delete("")
        assert result.status == Status.OK

        result = await repo.get("")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_list_keys(self, repo: SqliteRepository) -> None:
        """Test listing keys when there are less than 10 keys."""
        await repo.add("key1", ["value1"])
        await repo.add("key2", ["value2"])

        result = await repo.list_keys()
        assert result.status == Status.OK
        assert sorted(result.data) == ["key1", "key2"]

    async def test_list_keys_no_keys(self, repo: SqliteRepository) -> None:
        """Test listing keys when there are no keys in the database."""
        result = await repo.list_keys()
        assert result.status == Status.OK
        assert result.data == []

    async def test_list_keys_more_than_10(self, repo: SqliteRepository) -> None:
        """Test listing keys when there are more than 10 keys."""
        for i in range(15):
            await repo.add(f"key{i}", [f"value{i}"])

        result = await repo.list_keys()
        assert result.status == Status.OK
        assert len(result.data) == 10

    async def test_search_no_matches(self, repo: SqliteRepository) -> None:
        """Test searching with a term that matches no keys or values."""
        await repo.add("key1", ["value1"])
        result = await repo.search("nonexistent")
        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_search_empty_term(self, repo: SqliteRepository) -> None:
        """Test searching with an empty term."""
        await repo.add("key1", ["value1"])
        result = await repo.search("")

        assert result.status == Status.NO_KEY
        assert result.data == []

    async def test_search_matches_more_than_10(self, repo: SqliteRepository) -> None:
        """Test searching with a term that matches more than 10 keys."""
        for i in range(15):
            await repo.add(f"key{i}", [f"value{i}"])

        result = await repo.search("key")
        assert result.status == Status.OK
        assert len(result.data) == 10

    async def test_search_case_insensitivity(self, repo: SqliteRepository) -> None:
        """Test that search is case-insensitive."""
        await repo.add("Key1", ["Value1"])
        result = await repo.search("key1")
        assert result.status == Status.OK
        assert result.data == ["Key1"]

    async def test_add_and_get_multiple_keys(self, repo: SqliteRepository) -> None:
        """Test adding and getting multiple keys."""
        await repo.add("key1", ["value1"])
        await repo.add("key2", ["value2"])

        result1 = await repo.get("key1")
        result2 = await repo.get("key2")
        assert result1.status == Status.OK
        assert result1.data == ["value1"]
        assert result2.status == Status.OK
        assert result2.data == ["value2"]

    async def test_add_and_get_special_characters(self, repo: SqliteRepository) -> None:
        """Test adding keys and values with special characters."""
        special_key = "key!@#$%^&*()"
        special_value = "value!@#$%^&*()"
        await repo.add(special_key, [special_value])

        result = await repo.get(special_key)
        assert result.status == Status.OK
        assert result.data == [special_value]

    async def test_context_management(self, db_client: libsql_client.Client) -> None:
        """Test proper context management."""
        async with SqliteRepository(db_client=db_client) as repo:
            assert repo._client is not None

        assert db_client.closed

    async def test_add_none_values(self, repo: SqliteRepository) -> None:
        """Test adding None as values."""

        result = await repo.add("key1", None)  # type: ignore
        assert result.status == Status.NO_VALUES

    async def test_remove_none_values(self, repo: SqliteRepository) -> None:
        """Test removing None as values."""
        await repo.add("key1", ["value1"])

        result = await repo.remove("key1", None)  # type: ignore
        assert result.status == Status.NO_VALUES

    async def test_add_non_string_values(self, repo: SqliteRepository) -> None:
        """Test adding values that are not strings."""
        result = await repo.add("key1", [123, 456])  # type: ignore
        assert result.status == Status.OK

    async def test_remove_non_string_values(self, repo: SqliteRepository) -> None:
        """Test removing values that are not strings."""
        await repo.add("key1", ["value1"])
        result = await repo.remove("key1", [123])  # type: ignore
        assert result.status == Status.NO_VALUES


    async def test_concurrent_operations(self, repo: SqliteRepository) -> None:
        """Test concurrent add and remove operations."""
        await repo.add("key1", ["value1", "value2"])

        # Simulate concurrent removal and addition
        add_task = repo.add("key1", ["value3"])
        remove_task = repo.remove("key1", ["value1"])

        async with asyncio.TaskGroup() as tg:
            tg.create_task(add_task)
            tg.create_task(remove_task)

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == ["value2", "value3"]

    async def test_large_number_of_values(self, repo: SqliteRepository) -> None:
        """Test adding and retrieving a large number of values."""
        large_values = [f"value{i}" for i in range(1000)]
        await repo.add("key1", large_values)

        result = await repo.get("key1")
        assert result.status == Status.OK
        assert sorted(result.data) == sorted(large_values)
