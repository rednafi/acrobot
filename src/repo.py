import json
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self

import libsql_client

from src.db import get_db_client


class AddStatus(StrEnum):
    OK = "ok"


class RemoveStatus(StrEnum):
    NO_KEY = "no_key"
    NO_VALUES = "no_values"
    OK = "ok"


class DeleteStatus(StrEnum):
    NO_KEY = "no_key"
    OK = "ok"


class Repository(Protocol):
    """Protocol for database repository classes."""

    async def get(self, key: str) -> list[str]:
        """Get the set of values against a key."""
        ...

    async def list_alike_keys(self, key: str) -> list[str]:
        """Get similar keys."""
        ...

    async def list_keys(self) -> list[str]:
        """List all keys in the database."""
        ...

    async def add(self, key: str, values: list[str]) -> AddStatus:
        """Add values to the set against a key."""
        ...

    async def remove(self, key: str, values: list[str]) -> RemoveStatus:
        """Remove values from the set against a key."""
        ...

    async def delete(self, key: str) -> DeleteStatus:
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

    async def get(self, key: str) -> list[str]:
        """Get the set of values against a key."""

        query = libsql_client.Statement("SELECT val FROM acro WHERE key = ?", (key,))
        result_set = await self._client.execute(query)
        if not result_set.rows:
            return []
        return json.loads(result_set.rows[0]["val"])

    async def list_alike_keys(self, key: str) -> list[str]:
        """Get similar keys."""
        # Safely escape the input key for the MATCH clause

        # Explain this query in detail:
        # 1. The first part of the UNION ALL query uses the FTS5 MATCH operator to search for
        # keys that match the input key.

        # 2. The second part of the UNION ALL query uses the LIKE operator to search for keys
        # that contain the input key. It also ensures that the key does not match the input key
        # using a subquery with the FTS5 MATCH operator.

        # 3. The ORDER BY clause sorts the results by the rank of the FTS5 MATCH operator.

        # 4. The LIMIT clause limits the number of results to 10.

        query = libsql_client.Statement(
            """
            SELECT
                acro.key,
                bm25(acro_fts) AS rank
            FROM acro_fts
            JOIN acro ON acro_fts.rowid = acro.rowid
            WHERE acro_fts MATCH ?
            UNION ALL
            SELECT
                acro.key,
                NULL AS rank
            FROM acro
            WHERE acro.key LIKE '%' || ? || '%'
            AND NOT EXISTS (
                SELECT 1
                FROM acro_fts
                WHERE acro_fts MATCH ?
                AND acro_fts.rowid = acro.rowid
            )
            ORDER BY rank DESC
            LIMIT 10;
            """,
            (key, key, key)
        )

        result_set = await self._client.execute(query)
        return [row["key"] for row in result_set.rows]

    async def list_keys(self) -> list[str]:
        """List all keys in the database."""
        query = libsql_client.Statement("SELECT key FROM acro")
        result_set = await self._client.execute(query)
        return [row["key"] for row in result_set.rows]

    async def add(self, key: str, values: list[str]) -> AddStatus:
        """Add values to the set against a key."""
        existing_values = set(await self.get(key))
        updated_values = existing_values.union(values)

        query = libsql_client.Statement(
            "INSERT OR REPLACE INTO Acro (key, val) VALUES (?, ?)",
            (key, json.dumps(sorted(updated_values))),
        )
        await self._client.execute(query)
        return AddStatus.OK

    async def remove(self, key: str, values: list[str]) -> RemoveStatus:
        """Remove values from the set against a key."""
        existing_values = set(await self.get(key))
        updated_values = existing_values.difference(values)

        if not existing_values:
            return RemoveStatus.NO_KEY

        if not updated_values:  # If no values remain, delete the key
            await self.delete(key)
            return RemoveStatus.NO_VALUES

        query = libsql_client.Statement(
            "INSERT OR REPLACE INTO Acro (key, val) VALUES (?, ?)",
            (key, json.dumps(sorted(updated_values))),
        )
        await self._client.execute(query)
        return RemoveStatus.OK

    async def delete(self, key: str) -> DeleteStatus:
        """Delete a key and its associated values."""
        query = libsql_client.Statement("DELETE FROM acro WHERE key = ?", (key,))
        val = await self.get(key)
        await self._client.execute(query)
        return DeleteStatus.OK if val else DeleteStatus.NO_KEY
