from dataclasses import dataclass
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self

import libsql_client

from src.db import get_db_client


class Status(StrEnum):
    OK = "ok"
    NO_KEY = "no_key"
    NO_VALUES = "no_values"


@dataclass(frozen=True, slots=True)
class Result[T]:
    """Represents the result of a repository operation."""

    status: Status
    data: T


class Repository(Protocol):
    """Defines the interface for database repository implementations."""

    async def get(self, key: str) -> Result[list[str]]:
        """Retrieve the list of values associated with a key."""
        ...

    async def list_keys(self) -> Result[list[str]]:
        """Retrieve up to 10 random keys from the database."""
        ...

    async def search(self, term: str) -> Result[list[str]]:
        """Search for keys or values matching the term, returning up to 10 keys."""
        ...

    async def add(self, key: str, values: list[str]) -> Result[None]:
        """Add unique values to the list associated with a given key."""
        ...

    async def remove(self, key: str, values: list[str]) -> Result[None]:
        """Remove specified values from the list associated with a key."""
        ...

    async def delete(self, key: str) -> Result[None]:
        """Delete a key and its associated values."""
        ...


class SqliteRepository(Repository):
    """SQLite-backed repository for managing key-value data."""

    def __init__(self, db_client: libsql_client.Client | None = None) -> None:
        """
        Initialize the repository with an optional database client.
        If no client is provided, it will be created on entering the context.
        """
        self._client = db_client

    async def __aenter__(self) -> Self:
        """Initialize the database client if not already set."""
        if self._client is None:
            self._client = await get_db_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the database client if it was created during the context."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_value, traceback)
            self._client = None

    async def get(self, key: str) -> Result[list[str]]:
        """Retrieve the list of values associated with the given key."""
        assert isinstance(self._client, libsql_client.Client), "Client not initialized"

        query = libsql_client.Statement(
            "SELECT val FROM acro_kvs WHERE key = ?", (key,)
        )
        result_set = await self._client.execute(query)

        if not result_set.rows:
            return Result(status=Status.NO_KEY, data=[])

        data = [row["val"] for row in result_set.rows if row["val"]]
        return Result(status=Status.OK, data=data)

    async def list_keys(self) -> Result[list[str]]:
        """Retrieve up to 10 random keys from the database."""
        assert isinstance(self._client, libsql_client.Client), "Client not initialized"

        query = libsql_client.Statement(
            "SELECT DISTINCT key FROM acro_kvs ORDER BY RANDOM() LIMIT 10"
        )
        result_set = await self._client.execute(query)
        data = [row["key"] for row in result_set.rows]
        return Result(status=Status.OK, data=data)

    async def search(self, term: str) -> Result[list[str]]:
        """
        Search for keys or values matching the given term.
        Returns up to 10 keys.
        """
        assert isinstance(self._client, libsql_client.Client), "Client not initialized"

        if not term:
            return Result(status=Status.NO_KEY, data=[])

        term = term.lower()
        query = libsql_client.Statement(
            """
            WITH ranked_rows AS (
                SELECT rowid, rank
                FROM acro_kvs_fts
                WHERE key MATCH ? OR val MATCH ?
                ORDER BY rank
                LIMIT 10
            )
            SELECT DISTINCT acro_kvs.key
            FROM acro_kvs
            JOIN ranked_rows ON acro_kvs.rowid = ranked_rows.rowid
            ORDER BY ranked_rows.rank ASC
            """,
            (term, term),
        )
        result_set = await self._client.execute(query)

        data = [row["key"] for row in result_set.rows]
        if not data:
            return Result(status=Status.NO_KEY, data=[])

        return Result(status=Status.OK, data=data)

    async def add(self, key: str, values: list[str]) -> Result[None]:
        """
        Add unique values to the list associated with the given key.
        If no new values are provided, no changes are made.
        """
        assert isinstance(self._client, libsql_client.Client), "Client not initialized"

        if not values:
            return Result(status=Status.NO_VALUES, data=None)

        existing_result = await self.get(key)
        existing_values = set(existing_result.data)

        new_values = set(values) - existing_values
        if not new_values:
            return Result(status=Status.OK, data=None)

        tx = self._client.transaction()
        for val in new_values:
            await tx.execute(
                "INSERT INTO acro_kvs (key, val) VALUES (?, ?)", (key, val)
            )
        await tx.commit()

        return Result(status=Status.OK, data=None)

    async def remove(self, key: str, values: list[str]) -> Result[None]:
        """
        Remove specified values from the list associated with the given key.
        If the list becomes empty, the key is deleted from the database.
        """
        assert isinstance(self._client, libsql_client.Client), "Client not initialized"

        if not values:
            return Result(status=Status.NO_VALUES, data=None)

        existing_result = await self.get(key)
        if existing_result.status != Status.OK:
            return Result(status=Status.NO_KEY, data=None)

        existing_values = set(existing_result.data)
        values_to_remove = set(values)

        if not values_to_remove <= existing_values:
            return Result(status=Status.NO_VALUES, data=None)

        remaining_values = existing_values - values_to_remove

        if not remaining_values:
            await self.delete(key)
            return Result(status=Status.OK, data=None)

        tx = self._client.transaction()
        await tx.execute("DELETE FROM acro_kvs WHERE key = ?", (key,))
        for val in remaining_values:
            await tx.execute(
                "INSERT INTO acro_kvs (key, val) VALUES (?, ?)", (key, val)
            )
        await tx.commit()

        return Result(status=Status.OK, data=None)

    async def delete(self, key: str) -> Result[None]:
        """Delete the specified key and all associated values."""
        assert isinstance(self._client, libsql_client.Client), "Client not initialized"

        result = await self.get(key)
        if result.status != Status.OK:
            return Result(status=Status.NO_KEY, data=None)

        await self._client.execute(
            libsql_client.Statement("DELETE FROM acro_kvs WHERE key = ?", (key,))
        )
        return Result(status=Status.OK, data=None)
