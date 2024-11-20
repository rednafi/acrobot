import asyncio
import logging
import os
import signal

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src import settings
from src.cmds import acrobot
from src.db import init_db
from src.repo import SqliteRepository

logger = logging.getLogger("acrobot.main")


async def run_bot() -> None:
    """Initialize and run the Acrobot bot."""
    # Initialize the database and repository
    await init_db(settings.turso_database_url, settings.turso_auth_token, "sql/ddl.sql")
    repo = SqliteRepository()

    # Create the application
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.bot_data["repo"] = repo

    # Add command and message handlers
    application.add_handler(CommandHandler("acro", acrobot))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, acrobot))

    # Start the bot and listen for signals
    stop_event = asyncio.Event()

    def handle_signal() -> None:
        """Signal handler to trigger shutdown."""
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, handle_signal)
    loop.add_signal_handler(signal.SIGTERM, handle_signal)

    try:
        # Start the bot application
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await stop_event.wait()  # Wait for a stop signal
    finally:
        # Gracefully shut down the bot with a timeout
        logger.info("Shutting down the bot...")
        try:
            async with asyncio.timeout(3):  # Timeout in 3 seconds
                await shutdown_bot(application)
        except asyncio.TimeoutError:
            logger.error("Shutdown timed out, forcing exit...")
            os.kill(os.getpid(), signal.SIGKILL)


async def shutdown_bot(application: Application) -> None:
    """Shutdown the bot gracefully."""
    if application.updater.running:
        await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("Bot shut down gracefully.")


def main() -> None:
    """Entry point for running the bot."""
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down the bot...")


if __name__ == "__main__":
    main()
