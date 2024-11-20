import asyncio
import logging

import libsql_client

from src import settings

logger = logging.getLogger("acrobot.db")

# Global variable to store the database client
_db_client = None


async def init_db(url: str, token: str, ddl_file_path: str) -> None:
    async with libsql_client.create_client(url, auth_token=token) as client:
        with open(ddl_file_path) as f:
            ddl = f.read()

        result_set = await client.execute(ddl)
        logger.info("Database initialized, rows affected: %s", result_set.rows_affected)


async def get_db_client() -> libsql_client.Client:
    global _db_client

    if _db_client:
        return _db_client

    _db_client = libsql_client.create_client(
        settings.turso_database_url, auth_token=settings.turso_auth_token
    )
    return _db_client


if __name__ == "__main__":

    async def main() -> None:
        url = settings.turso_database_url
        auth_token = settings.turso_auth_token
        await init_db(url, auth_token, "sql/ddl.sql")

        client = await get_db_client()

        async with client:
            await client.execute("DELETE FROM Acro")

            await client.execute("""
                    -- Inserting sample data into the Acro table
                    INSERT INTO Acro (key, val) VALUES
                    ('record1', '["value1", "value2", "value3"]'),
                    ('record2', '["itemA", "itemB"]');
            """)

            for row in await client.execute("SELECT * FROM Acro"):
                print(row)

    asyncio.run(main())
