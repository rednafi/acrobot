"""Database initialization and client management."""

import logging
import pathlib

import libsql_client
import sqlparse

from src import settings

logger = logging.getLogger("acrobot.db")


async def init_db(url: str, token: str, sql_dir: str) -> None:
    """Initialize the database schema."""
    sql_dir = pathlib.Path(sql_dir)

    async with libsql_client.create_client(url, auth_token=token) as client:
        with open(sql_dir / "ddl.sql") as ddl_stream:
            ddl = ddl_stream.read()

        for stmt in sqlparse.split(ddl):
            await client.execute(stmt)
        logger.info("Database initialized...")


async def get_db_client() -> libsql_client.Client:
    """
    Get a global database client, creating a new one if necessary.

    Ensures that a valid and open client is always returned.
    """

    return libsql_client.create_client(
        settings.turso_database_url, auth_token=settings.turso_auth_token
    )
