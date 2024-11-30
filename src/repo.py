import json
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self

import libsql_client

from src.db import get_db_client
from dataclasses import dataclass

class Status(StrEnum):
    OK = "ok"
    NO_KEY = "no_key"
    NO_VALUES = "no_values"

@dataclass(frozen=True, slots=True)
class Result[T]:
    status: Status
    data: T


class Repository(Protocol):
    """Protocol for database repository classes. There's no update to avoid accidental
    bulk overwrites."""

    async def get(self, key: str) -> Result[list[str]]:
        """Get the list of values against a key."""
        ...

    async def list_keys(self) -> list[str]:
        """List a few keys from the database."""
        ...

    async def search(self) -> Result[list[str]]:
        """Fuzzy search for keys and values and return a list of matching keys."""
        ...

    async def add(self, key: str, values: list[str]) -> Result[None]:
        """Add values to the list against a key."""
        ...

    async def remove(self, key: str, values: list[str]) -> Result[None]:
        """Remove values from the list against a key."""
        ...

    async def delete(self, key: str) -> Result[None]:
        """Delete a key and its associated values from the database."""
        ...


class SqliteRepository(Repository):
    """Repository class for managing the data in the database."""

    _client: libsql_client.Client

    def __init__(self, db_client: libsql_client.Client | None = None) -> None:
        """Initialize the repository with an optional database client."""
        self._client = db_client

    async def __aenter__(self) -> Self:
        """Enter the context manager."""
        self._client = await get_db_client() if not self._client else self._client
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the context manager."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_value, traceback)
            self._client = None

    async def get(self, key: str) -> Result[list[str]]:
        """Retrieve the list of values associated with a key."""

        query = libsql_client.Statement(
            "SELECT val FROM acro_kvs WHERE key = ?",
            (key,)
        )
        result_set = await self._client.execute(query)

        # Return early if no rows are found
        if not result_set.rows:
            return Result(status=Status.NO_KEY, data=[])

        # Extract the values directly from rows
        data = [row["val"] for row in result_set.rows if row["val"]]

        return Result(status=Status.OK, data=data)

    async def list_keys(self) -> list[str]:
        """List 10 keys from the database."""

        # Fetch 10 random keys
        query = libsql_client.Statement("SELECT DISTINCT key FROM acro_kvs ORDER BY RANDOM() LIMIT 10")
        result_set = await self._client.execute(query)
        return [row["key"] for row in result_set.rows]

    async def search(self, term: str) -> Result[list[str]]:
        """Search for keys and values that match the input term (case-insensitively) and return up
        to 10 matching keys."""

        query = libsql_client.Statement(
            """
            WITH ranked_rows AS (
                SELECT rowid, rank
                FROM acro_kvs_fts
                WHERE key MATCH ? OR val MATCH ?
                ORDER BY rank
                LIMIT 10
            )
            SELECT DISTINCT
                acro_kvs.key
            FROM acro_kvs
            JOIN ranked_rows ON acro_kvs.rowid = ranked_rows.rowid
            ORDER BY ranked_rows.rank ASC;
            """,
            (term.lower(), term.lower())  # Normalize input to lowercase
        )
        result_set = await self._client.execute(query)

        # Extract matching keys
        data = [row["key"] for row in result_set.rows]

        # Return early if no matches
        if not data:
            return Result(status=Status.NO_KEY, data=[])

        return Result(status=Status.OK, data=data)

    async def add(self, key: str, values: list[str]) -> Result[None]:
        """Add unique values to the list for a given key."""

        # Early return if no values are provided
        if not values:
            return Result(status=Status.NO_VALUES, data=None)

        # Retrieve the current values associated with the key
        existing_result = await self.get(key)
        existing_values = set(existing_result.data) if existing_result.data else set()

        # Remove duplicates and values already present in the list
        values = list(set(values) - existing_values)

        # Perform batch insert for the new values
        tx = self._client.transaction()
        for val in values:
            await tx.execute(
                "INSERT INTO acro_kvs (key, val) VALUES (?, ?)",
                (key, val)
            )
        await tx.commit()

        return Result(status=Status.OK, data=None)


    async def remove(self, key: str, values: list[str]) -> Result[None]:
        """Remove specified values from the list associated with the key."""

        # Fetch current values associated with the key
        current_values_result = await self.get(key)

        # If the key doesn't exist, return an error
        if current_values_result.status != Status.OK:
            return Result(status=Status.NO_KEY, data=None)

        # Convert existing values and values to remove into sets for easy difference calculation
        existing_values = set(current_values_result.data)
        values_to_remove = set(values)

        # If all the values to remove are not present in the existing values, return an error
        if not values_to_remove.issubset(existing_values):
            return Result(status=Status.NO_VALUES, data=None)

        # Calculate the updated list of values after removal
        remaining_values = existing_values - values_to_remove

        # If there are no values left after removal, delete the key
        if not remaining_values:
            await self.delete(key)
            return Result(status=Status.OK, data=None)

        # Perform batch deletion and insertion in a single transaction
        tx = self._client.transaction()
        # Remove all existing values for the key
        await tx.execute(
            "DELETE FROM acro_kvs WHERE key = ?",
            [key]
        )

        # Insert the remaining values after removal
        for val in remaining_values:
            await tx.execute(
                "INSERT INTO acro_kvs (key, val) VALUES (?, ?)",
                (key, val)
            )

        await tx.commit()

        return Result(status=Status.OK, data=None)

    async def delete(self, key: str) -> Result[None]:
        """Delete a key and its associated values."""
        val = await self.get(key)

        if not val:
            return Result(status=Status.NO_KEY, data=None)

        query = libsql_client.Statement("DELETE FROM acro_kvs WHERE key = ?", (key,))
        await self._client.execute(query)
        return Result(status=Status.OK if val else Status.NO_KEY, data=None)
