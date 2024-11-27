"""Database initialization and client management."""

import logging

import libsql_client

from src import settings
import sqlparse

logger = logging.getLogger("acrobot.db")


async def init_db(url: str, token: str, ddl_file_path: str) -> None:
    """Initialize the database schema."""
    async with libsql_client.create_client(url, auth_token=token) as client:
        with open(ddl_file_path) as f:
            ddl = f.read()

        await client.batch(sqlparse.split(ddl))
        logger.info("Database initialized...")


async def get_db_client() -> libsql_client.Client:
    """
    Get a global database client, creating a new one if necessary.

    Ensures that a valid and open client is always returned.
    """

    return libsql_client.create_client(
        settings.turso_database_url, auth_token=settings.turso_auth_token
    )
