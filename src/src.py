from src.repo import *
import asyncio

repo = SqliteRepository()

async def main() -> None:
    async with repo:
        result = await repo.get("hello")
        print("repo.get('hello'):", result)

        result = await repo.list_keys()
        print("repo.list_keys():", result)

        result = await repo.search("llo")
        print("repo.search('llo'):", result)

        result = await repo.add("hello", ["world", "dennis", "ritchie"])
        print("repo.add('hello', ['world', 'dennis', 'ritchie']):", await repo.get("hello"))

        result = await repo.remove("hello", ["world", "dennis"])

        print(await repo.get("hello"))



if __name__ == "__main__":
    asyncio.run(main())
