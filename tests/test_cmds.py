from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.ext import ContextTypes

from src.cmds import (
    acrobot,
    format_error_message,
    format_instruction_message,
    format_success_message,
    handle_add,
    handle_delete,
    handle_get,
    handle_list,
    handle_remove,
    handle_validation_error,
    parse_command_args,
)
from src.repo import AddStatus, DeleteStatus, RemoveStatus


@pytest.fixture
def canned_repo() -> AsyncMock:
    """Fixture for a mocked SqliteRepository."""
    return AsyncMock()


@pytest.fixture
def canned_update() -> MagicMock:
    """Fixture for a mocked Update object."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def canned_context(canned_repo: AsyncMock) -> MagicMock:
    """Fixture for a mocked Context object with canned repository."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.bot_data = {"repo": canned_repo}
    return context


### Tests for Formatting Functions ###
def test_format_error_message() -> None:
    """Test the format_error_message function."""
    result = format_error_message("This is an error.")
    assert result == "❌ *Error*: This is an error."


def test_format_success_message() -> None:
    """Test the format_success_message function."""
    result = format_success_message("Success!", "Details of the success.")
    assert result == "✅ *Success!*\n\nDetails of the success."


def test_format_instruction_message() -> None:
    """Test the format_instruction_message function."""
    result = format_instruction_message("Instructions", "Follow these steps.")
    assert result == "*Instructions*\n\nFollow these steps."


def test_handle_validation_error() -> None:
    """Test the handle_validation_error function."""
    error = ValueError("Invalid input")
    result = handle_validation_error(error)
    assert "Invalid input" in result
    assert "❌ *Error*" in result


### Tests for the Command Parser ###
def test_parse_command_args_valid() -> None:
    """Test the command parser with valid input."""
    key, values = parse_command_args('key "value one" value_two')
    assert key == "key"
    assert values == ["value one", "value_two"]


def test_parse_command_args_missing_key() -> None:
    """Test the command parser with missing key."""
    with pytest.raises(ValueError, match="Missing key argument."):
        parse_command_args("")


def test_parse_command_args_empty_key() -> None:
    """Test the command parser with an empty key."""
    with pytest.raises(ValueError, match="Key must be non-empty."):
        parse_command_args('"" value1')


def test_parse_command_args_missing_values() -> None:
    """Test the command parser with missing values."""
    with pytest.raises(ValueError, match="Values must not be empty."):
        parse_command_args("key", require_values=True)


### Tests for Command Handlers ###
async def test_handle_add(canned_repo: AsyncMock) -> None:
    """Test the add command."""
    canned_repo.add.return_value = AddStatus.OK

    args = ["add", "test_key", "val1", "val2"]
    response = await handle_add(canned_repo, args)

    canned_repo.add.assert_awaited_once_with("test_key", ["val1", "val2"])
    assert "Values added successfully" in response
    assert "test_key" in response


async def test_handle_get(canned_repo: AsyncMock) -> None:
    """Test the get command."""
    canned_repo.get.return_value = ["val1", "val2"]
    canned_repo.list_alike_keys.return_value = []

    args = ["get", "test_key"]
    response = await handle_get(canned_repo, args)

    canned_repo.get.assert_awaited_once_with("test_key")
    assert "Get values" in response
    assert "test_key" in response


async def test_handle_get_no_values(canned_repo: AsyncMock) -> None:
    """Test the get command with no values."""
    canned_repo.get.return_value = []
    canned_repo.list_alike_keys.return_value = ["key1", "key2"]

    args = ["get", "test_key"]
    response = await handle_get(canned_repo, args)

    assert "Values not found" in response
    assert "key1" in response
    assert "key2" in response


async def test_handle_remove(canned_repo: AsyncMock) -> None:
    """Test the remove command."""
    canned_repo.remove.return_value = RemoveStatus.OK

    args = ["remove", "test_key", "val1", "val2"]
    response = await handle_remove(canned_repo, args)

    canned_repo.remove.assert_awaited_once_with("test_key", ["val1", "val2"])
    assert "Values removed successfully" in response
    assert "test_key" in response


async def test_handle_delete(canned_repo: AsyncMock) -> None:
    """Test the delete command."""
    canned_repo.delete.return_value = DeleteStatus.OK

    args = ["delete", "test_key"]
    response = await handle_delete(canned_repo, args)

    canned_repo.delete.assert_awaited_once_with("test_key")
    assert "Key deleted successfully" in response
    assert "test_key" in response


async def test_handle_list(canned_repo: AsyncMock) -> None:
    """Test the list command."""
    canned_repo.list_keys.return_value = ["key1", "key2", "key3"]

    response = await handle_list(canned_repo)

    canned_repo.list_keys.assert_awaited_once()
    assert "List keys" in response
    assert "key1" in response
    assert "key2" in response


### Tests for Main Bot Handler ###
async def test_acrobot_add_command(
    canned_update: MagicMock, canned_context: MagicMock
) -> None:
    """Test the main bot handler for the add command."""
    canned_context.args = ["add", "test_key", "val1", "val2"]
    canned_context.bot_data["repo"].add.return_value = AddStatus.OK

    await acrobot(canned_update, canned_context)

    canned_update.message.reply_text.assert_awaited_once()
    response = canned_update.message.reply_text.call_args[0][0]
    assert "Values added successfully" in response


async def test_acrobot_unknown_command(
    canned_update: MagicMock, canned_context: MagicMock
) -> None:
    """Test the main bot handler with an unknown command."""
    canned_context.args = ["unknown"]

    await acrobot(canned_update, canned_context)

    canned_update.message.reply_text.assert_awaited_once()
    response = canned_update.message.reply_text.call_args[0][0]
    assert "Unknown command" in response
