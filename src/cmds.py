import logging
import shlex
from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError, model_validator
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.repo import SqliteRepository


# Commands Enum
class Commands(StrEnum):
    """String enum for supported Acrobot commands."""

    ADD = "add"
    GET = "get"
    REMOVE = "remove"
    DELETE = "delete"
    LIST = "list"


# Pydantic Models
class KeyCommandArgs(BaseModel):
    """Model for commands requiring only a key."""

    key: str = Field(..., min_length=1, description="Key must be non-empty.")


class KeyValCommandArgs(BaseModel):
    """Model for commands requiring a key and one or more values."""

    key: str = Field(..., min_length=1, description="Key must be non-empty.")
    values: list[str] = Field(..., min_items=1, description="Values must not be empty.")

    @model_validator(mode="after")
    def sanitize_values(cls, values: dict) -> dict:
        print(type(values))
        """Sanitize and handle comma-separated values."""
        if isinstance(values.get("values"), str):
            values["values"] = [
                v.strip() for v in values["values"].split(",") if v.strip()
            ]
        return values


# Helper Functions
def parse_command_args(
    command_args: str, require_values: bool = True
) -> tuple[str, list[str]]:
    """
    Parse command arguments, allowing spaces in keys and values.

    Args:
        command_args (str): The arguments passed to the command.
        require_values (bool): Whether values are required (default: True).

    Returns:
        tuple[str, list[str]]: A tuple of the key and a list of values.

    Example:
        /acro add "foo bar" hello, world, hello world
        → Key: `foo bar`, Values: ["hello", "world", "hello world"]
    """
    parts = shlex.split(command_args)
    if len(parts) < 1:
        raise ValueError("Invalid command format. Expected at least a key.")

    key = parts[0]
    if require_values and len(parts) < 2:
        raise ValueError("Invalid command format. Expected a key and values.")

    values = " ".join(parts[1:]).split(",") if require_values else []
    return key.strip(), [v.strip() for v in values if v.strip()]


def format_error_message(error_message: str) -> str:
    """Standard format for error messages."""
    return f"❌ *Error*: {error_message}"


def format_success_message(header: str, details: str) -> str:
    """Standard format for success messages."""
    return f"✅ *{header}*\n\n{details}"


def format_instruction_message(header: str, instructions: str) -> str:
    """Standard format for instructions."""
    return f"*{header}*\n\n{instructions}"


def handle_validation_error(e: ValidationError) -> str:
    """Log and format validation errors."""
    logging.error("Validation failed: %s", e.errors())
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
        success = await repo.add(key, values)

    if success:
        values_formatted = "\n".join(f"- {v}" for v in values)
        return format_success_message(
            "Values added successfully",
            f"*Key*\n\n`{key}`\n\n*Values*\n\n{values_formatted}",
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
            keys_formatted = "\n".join(f"- `{k}`" for k in alike_keys)
            return format_error_message(
                (
                    f"Values not found for key `{key}`. "
                    "Did you mean one of these?\n\n"
                    "*Similar keys\n\n*"
                    f"{keys_formatted}"
                )
            )

        return format_error_message(f"Values not found for key `{key}`.")

    values_formatted = "\n".join(f"- `{v}`" for v in values)
    return format_success_message(f"*{key}*", values_formatted)


async def handle_remove(repo: SqliteRepository, args: list[str]) -> str:
    """Handle the remove command."""
    try:
        command_args = " ".join(args[1:])
        key, values = parse_command_args(command_args)
    except ValueError as e:
        return format_error_message(str(e))

    async with repo:
        success = await repo.remove(key, values)

    if success:
        return format_success_message(
            "Values removed successfully", f"*Key*\n\n`{key}`"
        )
    return format_error_message(
        f"Failed to remove values for key `{key}`. Are you sure `{values}` exist?"
    )


async def handle_delete(repo: SqliteRepository, args: list[str]) -> str:
    """Handle the delete command."""
    try:
        command_args = " ".join(args[1:])
        key, _ = parse_command_args(command_args, require_values=False)
    except ValueError as e:
        return format_error_message(str(e))

    async with repo:
        success = await repo.delete(key)

    if success:
        return format_success_message("Key deleted successfully", f"*Key*\n\n`{key}`")
    return format_error_message(
        f"Failed to delete key `{key}`. Are you sure it exists?"
    )


async def handle_list(repo: SqliteRepository) -> str:
    """Handle the list command."""
    async with repo:
        keys = await repo.list_keys()

    if not keys:
        return format_error_message("No keys found in the database.")

    keys_formatted = "\n".join(f"- `{k}`" for k in keys)
    return format_success_message("Keys", keys_formatted)


# Main Bot Command Handler
async def acrobot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Acrobot commands."""
    if not update.message:
        logging.warning("Received an update with no message: %s", update)
        return

    if not context.args or len(context.args) < 1:
        instructions = (
            "1. *Add a key with values*\n"
            "   - `/acro add <key> <val1>, <val2>, ...`\n"
            '   - `/acro add "key with spaces" <val1>, <val2>, ...`\n\n'
            "2. *Retrieve values for a key*\n"
            "   - `/acro get <key>`\n"
            '   - `/acro get "key with spaces"`\n\n'
            "3. *Remove specific values*\n"
            "   - `/acro remove <key> <val1>, <val2>, ...`\n"
            '   - `/acro remove "key with spaces" <val1>, <val2>, ...`\n\n'
            "4. *Delete a key*\n"
            "   - `/acro delete <key>`\n"
            '   - `/acro delete "key with spaces"`\n\n'
            "5. *List all keys*\n"
            "   - `/acro list`\n"
        )

        await update.message.reply_text(
            format_instruction_message(
                "🤖 Acrobot - avoid acronym acrobats!", instructions
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
                response = format_error_message(
                    "Unknown command. Use `/acro` to see available commands."
                )

        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logging.exception("An error occurred while processing the command.")
        await update.message.reply_text(
            format_error_message(
                "An unexpected error occurred. Please try again later."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
