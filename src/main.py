# pragma: no cover

import asyncio
import logging
import os
import signal

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src import settings
from src.cmds import acrobot
from src.db import init_db
from src.log import configure_logger
from src.repo import SqliteRepository

logger = logging.getLogger("acrobot.main")


async def setup_application(repo: SqliteRepository) -> Application:
    """Setup the bot application with handlers and data."""
    application = Application.builder().token(settings.telegram_bot_token).build()

    application.bot_data["repo"] = repo

    # Add command and message handlers
    application.add_handler(CommandHandler("acro", acrobot))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, acrobot))
    return application


async def run_bot() -> None:
    """Initialize and run the Acrobot bot."""
    # Initialize database and repository
    await init_db(
        settings.turso_database_url,
        settings.turso_auth_token,
        "sql/",
    )
    repo = SqliteRepository()

    # Setup application
    application: Application = await setup_application(repo)

    # Graceful shutdown with asyncio.Event
    stop_event = asyncio.Event()

    def stop_loop(*_: object) -> None:
        logger.info("Shutdown signal received.")
        stop_event.set()

    signal.signal(signal.SIGINT, stop_loop)
    signal.signal(signal.SIGTERM, stop_loop)

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot is running...")
        await stop_event.wait()
    finally:
        logger.info("Shutting down the bot...")
        try:
            # Stop the updater before stopping the application
            if application.updater.running:
                await application.updater.stop()
            await application.stop()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            await application.shutdown()  # Clean up resources
            logger.info("Bot shut down gracefully.")


def main() -> None:
    """Entry point for running the bot."""
    configure_logger()

    # Log the current process ID
    logger.info("Starting the bot on process %d", os.getpid())

    # Log the current environment
    logger.info("Running in %s environment", os.environ.get("ENVIRONMENT", "local"))

    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")


if __name__ == "__main__":
    main()
