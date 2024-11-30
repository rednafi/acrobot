from src.repo import *
import asyncio

repo = SqliteRepository()

async def main() -> None:
    async with repo:
        result = await repo.add("key1", [])
        assert result.status == Status.NO_VALUES

        result = await repo.get("key1")
        assert result.status == Status.NO_KEY
        assert result.data == []



if __name__ == "__main__":
    asyncio.run(main())
