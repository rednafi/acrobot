# test_cmds.py

from unittest.mock import AsyncMock

import pytest

from src.cmds import (
    format_error_message,
    format_instruction_message,
    format_success_message,
    handle_add,
    handle_delete,
    handle_get,
    handle_list,
    handle_remove,
    handle_search,
    handle_validation_error,
    parse_command_args,
)
from src.repo import Result, SqliteRepository, Status


# Utility Functions Tests
def test_parse_command_args_valid() -> None:
    key, values = parse_command_args("key1 value1 value2")
    assert key == "key1"
    assert values == ["value1", "value2"]


def test_parse_command_args_with_spaces() -> None:
    key, values = parse_command_args('"key with spaces" "value with spaces" value2')
    assert key == "key with spaces"
    assert values == ["value with spaces", "value2"]


def test_parse_command_args_missing_key() -> None:
    with pytest.raises(ValueError, match="Missing key argument."):
        parse_command_args("")


def test_parse_command_args_empty_key() -> None:
    with pytest.raises(ValueError, match="Key must be non-empty."):
        parse_command_args('"" value1')


def test_parse_command_args_require_values() -> None:
    with pytest.raises(ValueError, match="Values must not be empty."):
        parse_command_args("key1")


def test_parse_command_args_not_require_values() -> None:
    key, values = parse_command_args("key1", require_values=False)
    assert key == "key1"
    assert values == []


def test_format_error_message() -> None:
    error_message = format_error_message("An error occurred.")
    assert error_message == "❌ *Error*: An error occurred."


def test_format_success_message() -> None:
    success_message = format_success_message("Success", "Details here.")
    assert success_message == "✅ *Success*\n\nDetails here."


def test_format_instruction_message() -> None:
    instruction_message = format_instruction_message("Instructions", "Do this.")
    assert instruction_message == "*Instructions*\n\nDo this."


def test_handle_validation_error(caplog: pytest.LogCaptureFixture) -> None:
    error = ValueError("Invalid input.")
    message = handle_validation_error(error)
    assert "Validation failed: Invalid input." in caplog.text
    assert message == format_error_message(
        "Invalid input. Make sure your command matches the expected format."
    )


# Command Handlers Tests
@pytest.fixture
def repo_mock() -> SqliteRepository:
    """Fixture to create a mock repository."""
    repo = AsyncMock(spec=SqliteRepository)
    return repo


@pytest.fixture
def context_args() -> list[str]:
    """Fixture to provide default context arguments."""
    return ["command", "key1", "value1", "value2"]


# Helper function to create a fake Result object
def create_result(status: Status, data: list[str] | None) -> Result:
    return Result(status=status, data=data)


# Tests for handle_add
async def test_handle_add_success(repo_mock: AsyncMock) -> None:
    repo_mock.add.return_value = create_result(Status.OK, None)

    response = await handle_add(repo_mock, ["add", "key1", "value1", "value2"])
    expected_response = format_success_message(
        "Values added successfully",
        "*Key*\n```\nkey1\n```\n\n*Values*\n```\n- value1\n- value2\n```",
    )
    assert response == expected_response
    repo_mock.add.assert_awaited_once_with("key1", ["value1", "value2"])


async def test_handle_add_missing_key(repo_mock: AsyncMock) -> None:
    response = await handle_add(repo_mock, ["add"])
    assert response == format_error_message("Missing key argument.")


async def test_handle_add_no_values(repo_mock: AsyncMock) -> None:
    response = await handle_add(repo_mock, ["add", "key1"])
    assert response == format_error_message("Values must not be empty.")


async def test_handle_add_failure(repo_mock: AsyncMock) -> None:
    repo_mock.add.return_value = create_result(Status.NO_VALUES, None)

    response = await handle_add(repo_mock, ["add", "key1", "value1"])
    assert response == format_error_message("Failed to add values for key `key1`.")


# Tests for handle_get
async def test_handle_get_success(repo_mock: AsyncMock) -> None:
    repo_mock.get.return_value = create_result(Status.OK, ["value1", "value2"])
    repo_mock.search.return_value = create_result(Status.OK, [])

    response = await handle_get(repo_mock, ["get", "key1"])
    expected_response = format_success_message(
        "Get values",
        "*Key*\n```\nkey1\n```\n\n*Values*\n```\n- value1\n- value2\n```",
    )
    assert response == expected_response
    repo_mock.get.assert_awaited_once_with("key1")
    repo_mock.search.assert_awaited_once_with("key1")


async def test_handle_get_key_not_found_no_alike(repo_mock: AsyncMock) -> None:
    repo_mock.get.return_value = create_result(Status.NO_KEY, [])
    repo_mock.search.return_value = create_result(Status.NO_KEY, [])

    response = await handle_get(repo_mock, ["get", "key1"])
    assert response == format_error_message("Values not found for key `key1`.")
    repo_mock.get.assert_awaited_once_with("key1")
    repo_mock.search.assert_awaited_once_with("key1")


async def test_handle_get_key_not_found_with_alike(repo_mock: AsyncMock) -> None:
    repo_mock.get.return_value = create_result(Status.NO_KEY, [])
    repo_mock.search.return_value = create_result(Status.OK, ["key2", "key3"])

    response = await handle_get(repo_mock, ["get", "key1"])
    expected_response = format_error_message(
        "Values not found for key `key1`. Did you mean one of these?\n\n"
        "*Keys*\n"
        "```\n- key2\n- key3\n```"
    )
    assert response == expected_response
    repo_mock.get.assert_awaited_once_with("key1")
    repo_mock.search.assert_awaited_once_with("key1")


async def test_handle_get_with_extra_values(repo_mock: AsyncMock) -> None:
    response = await handle_get(repo_mock, ["get", "key1", "value1"])
    assert response == format_error_message(
        "Only the values for a single key can be retrieved at a time."
    )


async def test_handle_get_missing_key(repo_mock: AsyncMock) -> None:
    response = await handle_get(repo_mock, ["get"])
    assert response == format_error_message("Missing key argument.")


# Tests for handle_search
async def test_handle_search_success(repo_mock: AsyncMock) -> None:
    repo_mock.search.return_value = create_result(Status.OK, ["key1", "key2"])

    response = await handle_search(repo_mock, ["search", "key"])
    expected_response = format_success_message(
        "Search results",
        "*Keys*\n```\n- key1\n- key2\n```",
    )
    assert response == expected_response
    repo_mock.search.assert_awaited_once_with("key")


async def test_handle_search_no_matches(repo_mock: AsyncMock) -> None:
    repo_mock.search.return_value = create_result(Status.NO_KEY, [])

    response = await handle_search(repo_mock, ["search", "nonexistent"])
    assert response == format_error_message("No keys found similar to `nonexistent`.")
    repo_mock.search.assert_awaited_once_with("nonexistent")


async def test_handle_search_extra_values(repo_mock: AsyncMock) -> None:
    response = await handle_search(repo_mock, ["search", "key1", "key2"])
    assert response == format_error_message(
        "Only a single key can be searched at a time."
    )


async def test_handle_search_missing_key(repo_mock: AsyncMock) -> None:
    response = await handle_search(repo_mock, ["search"])
    assert response == format_error_message("Missing key argument.")


# Tests for handle_remove
async def test_handle_remove_success(repo_mock: AsyncMock) -> None:
    repo_mock.remove.return_value = create_result(Status.OK, None)

    response = await handle_remove(repo_mock, ["remove", "key1", "value1", "value2"])
    expected_response = format_success_message(
        "Values removed successfully",
        "*Key*\n\n`key1`\n\n*Values*\n```\n- value1\n- value2\n```",
    )
    assert response == expected_response
    repo_mock.remove.assert_awaited_once_with("key1", ["value1", "value2"])


async def test_handle_remove_no_key(repo_mock: AsyncMock) -> None:
    repo_mock.remove.return_value = create_result(Status.NO_KEY, None)

    response = await handle_remove(repo_mock, ["remove", "key1", "value1"])
    assert response == format_error_message("Key `key1` not found.")
    repo_mock.remove.assert_awaited_once_with("key1", ["value1"])


async def test_handle_remove_no_values(repo_mock: AsyncMock) -> None:
    repo_mock.remove.return_value = create_result(Status.NO_VALUES, None)

    response = await handle_remove(repo_mock, ["remove", "key1", "value1"])
    expected_response = format_error_message(
        "Values not found.\n\n*Key*\n```\nkey1\n```\n\n*Values*\n```\n- value1\n```"
    )
    assert response == expected_response
    repo_mock.remove.assert_awaited_once_with("key1", ["value1"])


async def test_handle_remove_missing_values(repo_mock: AsyncMock) -> None:
    response = await handle_remove(repo_mock, ["remove", "key1"])
    assert response == format_error_message("Values must not be empty.")


async def test_handle_remove_missing_key(repo_mock: AsyncMock) -> None:
    response = await handle_remove(repo_mock, ["remove"])
    assert response == format_error_message("Missing key argument.")


# Tests for handle_delete
async def test_handle_delete_success(repo_mock: AsyncMock) -> None:
    repo_mock.delete.return_value = create_result(Status.OK, None)

    response = await handle_delete(repo_mock, ["delete", "key1"])
    expected_response = format_success_message(
        "Key deleted successfully", "*Key*\n```\nkey1\n```"
    )
    assert response == expected_response
    repo_mock.delete.assert_awaited_once_with("key1")


async def test_handle_delete_no_key(repo_mock: AsyncMock) -> None:
    repo_mock.delete.return_value = create_result(Status.NO_KEY, None)

    response = await handle_delete(repo_mock, ["delete", "key1"])
    assert response == format_error_message("Key `key1` not found.")
    repo_mock.delete.assert_awaited_once_with("key1")


async def test_handle_delete_missing_key(repo_mock: AsyncMock) -> None:
    response = await handle_delete(repo_mock, ["delete"])
    assert response == format_error_message("Missing key argument.")


# Tests for handle_list
async def test_handle_list_success(repo_mock: AsyncMock) -> None:
    repo_mock.list_keys.return_value = create_result(Status.OK, ["key1", "key2"])

    response = await handle_list(repo_mock)
    expected_response = format_success_message(
        "List 10 random keys", "*Keys*\n```\n- key1\n- key2\n```"
    )
    assert response == expected_response
    repo_mock.list_keys.assert_awaited_once()


async def test_handle_list_no_keys(repo_mock: AsyncMock) -> None:
    repo_mock.list_keys.return_value = create_result(Status.OK, [])

    response = await handle_list(repo_mock)
    assert response == format_error_message("No keys found.")
    repo_mock.list_keys.assert_awaited_once()
