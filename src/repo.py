import json
from types import TracebackType
from typing import Protocol, Self

import libsql_client

from src.db import get_db_client


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

    async def add(self, key: str, values: list[str]) -> bool:
        """Add values to the set against a key."""
        ...

    async def remove(self, key: str, values: list[str]) -> bool:
        """Remove values from the set against a key."""
        ...

    async def delete(self, key: str) -> bool:
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
        query = libsql_client.Statement("SELECT val FROM Acro WHERE key = ?", (key,))
        result_set = await self._client.execute(query)
        if not result_set.rows:
            return []
        return json.loads(result_set.rows[0]["val"])

    async def list_alike_keys(self, key: str) -> list[str]:
        """Get similar keys."""
        # Safely escape the input key for the MATCH clause

        # Explain this query in detail:
        # 1. The first SELECT statement uses the FTS5 extension to perform a full-text search
        # on the key column.

        # 2. The second SELECT statement uses the LIKE operator to perform a substring match on
        # the key column.

        # 3. The UNION operator combines the results of the two SELECT statements.

        # 4. The ORDER BY clause sorts the results by the rank of the full-text search. The rank
        # is calculated using the BM25 algorithm.

        # 5. The LIMIT clause limits the number of results to 10.
        query = libsql_client.Statement(
        f"""
        SELECT
            acro.key,
            bm25(fts5_key) AS rank
        FROM fts5_key
        JOIN acro ON fts5_key.rowid = acro.rowid
        WHERE fts5_key MATCH ?  -- Full-text search
        UNION
        SELECT
            acro.key,
            NULL AS rank
        FROM acro
        WHERE acro.key LIKE '%' || ? || '%' -- Substring match
        ORDER BY rank ASC
        LIMIT 10;
        """,
        (key, key),
        )
        result_set = await self._client.execute(query)
        return [row["key"] for row in result_set.rows]

    async def list_keys(self) -> list[str]:
        """List all keys in the database."""
        query = libsql_client.Statement("SELECT key FROM Acro")
        result_set = await self._client.execute(query)
        return [row["key"] for row in result_set.rows]

    async def add(self, key: str, values: list[str]) -> bool:
        """Add values to the set against a key. Return True if successful."""
        existing_values = set(await self.get(key))
        updated_values = existing_values.union(values)

        query = libsql_client.Statement(
            "INSERT OR REPLACE INTO Acro (key, val) VALUES (?, ?)",
            (key, json.dumps(sorted(updated_values))),
        )
        await self._client.execute(query)
        return True

    async def remove(self, key: str, values: list[str]) -> bool:
        """Remove values from the set against a key. Return True if successful."""
        existing_values = set(await self.get(key))
        updated_values = existing_values.difference(values)

        if not updated_values:  # If no values remain, delete the key
            return await self.delete(key)

        query = libsql_client.Statement(
            "INSERT OR REPLACE INTO Acro (key, val) VALUES (?, ?)",
            (key, json.dumps(sorted(updated_values))),
        )
        await self._client.execute(query)
        return existing_values != updated_values

    async def delete(self, key: str) -> bool:
        """Delete a key and its associated values. Return True if successful."""
        query = libsql_client.Statement("DELETE FROM Acro WHERE key = ?", (key,))
        val = await self.get(key)
        await self._client.execute(query)
        return bool(val)
