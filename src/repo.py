"""Repository class for managing the data in the database."""

import json
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

import libsql_client

from src.db import get_db_client


class Repository(ABC):
    """Protocol for database repository classes."""

    @abstractmethod
    async def get(self, key: str) -> list[str]:
        """Get a value from the database."""
        ...

    @abstractmethod
    async def list_keys(self) -> list[str]:
        """List all keys in the database."""
        ...

    @abstractmethod
    async def set(self, key: str, values: list[str]) -> None:
        """Set a value in the database."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from the database."""
        ...


class AcroRepository(Repository):
    """Repository class for managing the data in the database."""

    _db_client: libsql_client.Client
    _client: libsql_client.Client

    async def __aenter__(self) -> Self:
        """Enter the runtime context for the repository."""
        self._db_client = await get_db_client()
        self._client = await self._db_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the runtime context for the repository."""
        await self._db_client.__aexit__(exc_type, exc_val, exc_tb)

    async def get(self, key: str) -> list[str]:
        """Get a value from the database."""
        query = libsql_client.Statement("SELECT val FROM Acro WHERE key = ?", (key,))
        result_set = await self._client.execute(query)
        if not result_set:
            return []
        # Assuming val is stored as a JSON string in the database
        return json.loads(result_set[0]["val"])

    async def list_keys(self) -> list[str]:
        """List all keys in the database."""
        query = libsql_client.Statement("SELECT key FROM Acro")
        result_set = await self._client.execute(query)
        return [row["key"] for row in result_set]

    async def set(self, key: str, values: list[str]) -> None:
        """Set a value in the database."""
        query = libsql_client.Statement(
            "INSERT OR REPLACE INTO Acro (key, val) VALUES (?, ?)",
            (key, json.dumps(values)),  # Serialize list to JSON string
        )
        await self._client.execute(query)

    async def delete(self, key: str) -> None:
        """Delete a value from the database."""
        query = libsql_client.Statement("DELETE FROM Acro WHERE key = ?", (key,))
        await self._client.execute(query)


if __name__ == "__main__":

    async def main() -> None:
        async with AcroRepository() as repo:
            await repo.set("record1", ["value1", "value2"])
            await repo.set("record2", ["itemA", "itemB"])

            print("Before replace:")
            for key in await repo.list_keys():
                print(key, await repo.get(key))

            # Replace records
            await repo.set("record1", ["new_value"])
            await repo.set("record2", ["itemC", "itemD"])

            print("\nAfter replace:")
            for key in await repo.list_keys():
                print(key, await repo.get(key))

            # Clean up
            await repo.delete("record1")
            await repo.delete("record2")

    import asyncio

    asyncio.run(main())
