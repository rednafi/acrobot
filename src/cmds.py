import logging
import shlex
from enum import StrEnum

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.repo import RemoveStatus, SqliteRepository


# Commands Enum
class Commands(StrEnum):
    """String enum for supported Acrobot commands."""

    ADD = "add"
    GET = "get"
    REMOVE = "remove"
    DELETE = "delete"
    LIST = "list"


def parse_command_args(
    command_args: str, require_values: bool = True
) -> tuple[str, list[str]]:
    """
    Parse command arguments, allowing spaces in keys and values.
    Exactly how Unix command line arguments are parsed.
    """

    # Split the command arguments
    args = shlex.split(command_args)

    if len(args) < 1:
        raise ValueError("Missing key argument.")

    key = args[0]
    values = args[1:] if len(args) > 1 else []

    if not key:
        raise ValueError("Key must be non-empty.")

    if require_values and not values:
        raise ValueError("Values must not be empty.")

    return key, values


def format_error_message(error_message: str) -> str:
    """Standard format for error messages."""
    return f"❌ *Error*: {error_message}"


def format_success_message(header: str, details: str) -> str:
    """Standard format for success messages."""
    return f"✅ *{header}*\n\n{details}"


def format_instruction_message(header: str, instructions: str) -> str:
    """Standard format for instructions."""
    return f"*{header}*\n\n{instructions}"


def handle_validation_error(e: ValueError) -> str:
    """Log and format validation errors."""
    logging.error("Validation failed: %s", e)
    return format_error_message(
        "Invalid input. Make sure your command matches the expected format."
    )


# Command Handlers
async def handle_add(repo: SqliteRepository, args: list[str]) -> str:
    """Handle the add command."""
    try:
        command_args = " ".join(args[1:])
        key, values = parse_command_args(command_args)
    except ValueError as e:
        return format_error_message(str(e))

    async with repo:
        status = await repo.add(key, values)

    if status == RemoveStatus.OK:
        values_formatted = "\n".join(f"- {v}" for v in values)
        return format_success_message(
            "Values added successfully",
            f"*Key*\n```\n{key}\n```\n\n*Values*\n```\n{values_formatted}\n```",
        )
    return format_error_message(f"Failed to add values for key `{key}`.")


async def handle_get(repo: SqliteRepository, args: list[str]) -> str:
    """Handle the get command."""
    try:
        command_args = " ".join(args[1:])
        key, _ = parse_command_args(command_args, require_values=False)
    except ValueError as e:
        return format_error_message(str(e))

    async with repo:
        values = await repo.get(key)
        alike_keys = await repo.list_alike_keys(key)

    if not values:
        if alike_keys:
            keys_formatted = "\n".join(f"- {k}" for k in alike_keys)
            return format_error_message(
                (
                    f"Values not found for key `{key}`. "
                    "Did you mean one of these?\n\n"
                    "*Keys*\n"
                    "```\n"
                    f"{keys_formatted}"
                    "\n```"
                )
            )

        return format_error_message(f"Values not found for key `{key}`.")

    values_formatted = "\n".join(f"- {v}" for v in values)
    return format_success_message(
        "Get values",
        f"*Key*\n```\n{key}\n```\n\n*Values*\n```\n{values_formatted}\n```",
    )


async def handle_remove(repo: SqliteRepository, args: list[str]) -> str:
    """Handle the remove command."""
    try:
        command_args = " ".join(args[1:])
        key, values = parse_command_args(command_args)
    except ValueError as e:
        return format_error_message(str(e))

    async with repo:
        status = await repo.remove(key, values)

    values_formatted = "\n".join(f"- {v}" for v in values)
    if status == RemoveStatus.OK:
        return format_success_message(
            "Values removed successfully",
            f"*Key*\n\n`{key}`\n\n*Values*\n```\n{values_formatted}\n```",
        )

    if status == RemoveStatus.NO_KEY:
        return format_error_message(f"Key `{key}` not found.")

    if status == RemoveStatus.NO_VALUES:
        return format_error_message(
            f"Values not found.\n\n*Key*\n```\n{key}\n```\n\n*Values*\n```\n{values_formatted}\n```"
        )


async def handle_delete(repo: SqliteRepository, args: list[str]) -> str:
    """Handle the delete command."""
    try:
        command_args = " ".join(args[1:])
        key, _ = parse_command_args(command_args, require_values=False)
    except ValueError as e:
        return format_error_message(str(e))

    async with repo:
        status = await repo.delete(key)

    if status == RemoveStatus.OK:
        return format_success_message(
            "Key deleted successfully", f"*Key*\n```\n{key}\n```"
        )
    return format_error_message(f"Key `{key}` not found.")


async def handle_list(repo: SqliteRepository) -> str:
    """Handle the list command."""
    async with repo:
        keys = await repo.list_keys()

    if not keys:
        return format_error_message("No keys found.")

    keys_formatted = "\n".join(f"- {k}" for k in keys)
    return format_success_message("List keys", f"*Keys*\n```\n{keys_formatted}\n```")


# Main Bot Command Handler
async def acrobot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Acrobot commands."""
    if not update.message:
        logging.debug("Received an update with no message.")
        return

    instructions = (
        "1. *Add a key with values*\n"
        "```\n"
        "- /acro add <key> <val1> <val2> ...\n"
        '- /acro add "key with spaces" <val1> <val2> ...\n'
        '- /acro add <key> "value with spaces"\n\n'
        "Just like how Unix parses command line arguments."
        "```\n\n"
        "2. *Retrieve values for a key*\n"
        "```\n"
        "- /acro get <key>\n"
        '- /acro get "key with spaces"\n'
        "```\n\n"
        "3. *Remove specific values*\n"
        "```\n"
        "- /acro remove <key> <val1> <val2> ...\n"
        '- /acro remove "key with spaces" <val1> <val2> ...\n'
        "```\n\n"
        "4. *Delete a key*\n"
        "```\n"
        "- /acro delete <key>\n"
        '- /acro delete "key with spaces"\n'
        "```\n\n"
        "5. *List all keys*\n"
        "```\n"
        "- /acro list\n"
        "```\n\n"
    )

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            format_instruction_message(
                "🤖 Acrobot - avoid acronym acrobatics!", instructions
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    command = context.args[0].lower()
    repo: SqliteRepository = context.bot_data.get("repo")

    if not repo:
        await update.message.reply_text(
            format_error_message("Repository not initialized."),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        match command:
            case Commands.ADD:
                response = await handle_add(repo, context.args)
            case Commands.GET:
                response = await handle_get(repo, context.args)
            case Commands.REMOVE:
                response = await handle_remove(repo, context.args)
            case Commands.DELETE:
                response = await handle_delete(repo, context.args)
            case Commands.LIST:
                response = await handle_list(repo)
            case _:
                response = format_error_message(f"Unknown command.\n\n{instructions}")

        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logging.exception("An error occurred while processing the command.")
        await update.message.reply_text(
            format_error_message(
                "An unexpected error occurred. Please try again later."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
