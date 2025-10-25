import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, mock_open, patch

import pytest
from _pytest.logging import LogCaptureFixture
from google.genai.types import File, FileState

from packages.utilities.errors import HandleAttachmentError
from packages.utilities.file_utils import (
    _append_secret,
    check_for_file_active,
    handle_attachment,
    read_config,
    read_temp_config,
    save_temp_config,
    save_wave_file,
    validate_config_files,
    wait_for_file_active,
)

VALID_CONFIG = {
    "GeminiAPIkey": "key-123",
    "DiscordToken": "token-xyz",
    "OwnerID": "1234567890",
    "ModelNames": {"default": "gemini-pro"},
    "SystemPrompts": ["You are a helpful assistant."],
    "HarmBlockThreshold": "BLOCK_NONE",
    "Temperature": 0.9,
}

def test_check_for_file_active() -> None:
    """Checks if tested function is working for uploaded files."""
    result = check_for_file_active(File(state=FileState.ACTIVE))
    assert result

def test_check_for_file_not_active() -> None:
    """Checks if tested function is working for uploaded files."""
    result = check_for_file_active(File(state=FileState.PROCESSING))
    assert not result

def test_check_for_file_failed() -> None:
    """Checks if tested function raises when file is failed to process."""
    with pytest.raises(RuntimeError):
        check_for_file_active(File(state=FileState.FAILED))

@patch(
    "packages.utilities.file_utils.check_for_file_active",
    side_effect=[
        False,
        False,
        True,
    ],
)
@pytest.mark.asyncio
async def test_wait_for_file_active_success(
    mock_check_for_file_active: MagicMock,
) -> None:
    """Checks if the function waits correctly and returns when the file becomes active.

    This test simulates the state changing from PROCESSING to ACTIVE.
    """
    total_side_effects = 3

    await wait_for_file_active(File(), interval=0.01) # doesn't matter

    assert mock_check_for_file_active.call_count == total_side_effects

@patch(
    "packages.utilities.file_utils.check_for_file_active",
    side_effect=[
        False,
        False,
        RuntimeError("File failed to process!"),
    ],
)
@pytest.mark.asyncio
async def test_wait_for_file_active_failed(
    mock_check_for_file_active: MagicMock,
) -> None:
    """Checks if the function waits correctly and returns when the file becomes active.

    This test simulates the state changing from PROCESSING to ACTIVE.
    """
    total_side_effects = 3

    with pytest.raises(RuntimeError):
        await wait_for_file_active(File(), interval=0.01) # doesn't matter

    assert mock_check_for_file_active.call_count == total_side_effects


@patch(
    "packages.utilities.file_utils.check_for_file_active",
    return_value=False,
)
@pytest.mark.asyncio
async def test_wait_for_file_active_timeout(
    mock_check_for_file_active: MagicMock,
    caplog: LogCaptureFixture,
) -> None:
    """Checks if the function waits correctly and returns when the file becomes active.

    This test simulates the state changing from PROCESSING to ACTIVE.
    """
    total_side_effects = 2  # once at 0s and one more at 0.01s
    caplog.set_level(logging.WARNING)

    await wait_for_file_active(File(), interval=0.01, timeout=0.01)

    assert mock_check_for_file_active.call_count == total_side_effects
    assert "Timeout while waiting for file" in caplog.text

@patch("packages.utilities.file_utils.logger")
@patch(
    "packages.utilities.file_utils.generate_unique_file_name",
    return_value="unique-file-name.png",
)
@pytest.mark.asyncio
async def test_handle_attachment_success(
    mock_generate_unique_file_name: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Tests the successful execution.

    Asserts that logger.info is called with the expected messages.
    """
    expected_log_counts = 2

    mock_attachment = AsyncMock()
    mock_attachment.filename = "test_image.png"
    mock_attachment.content_type = "image/png"

    mock_uploaded_file = MagicMock()
    mock_uploaded_file.display_name = "unique-file-name.png"
    mock_uploaded_file.name = "files/abc-123"

    mock_client = MagicMock()
    mock_client.files.upload.return_value = mock_uploaded_file

    expected_local_path = "./temp/unique-file-name.png"
    file_names, uploaded_files = await handle_attachment(mock_attachment, mock_client)

    assert file_names == [expected_local_path]
    assert uploaded_files == [mock_uploaded_file]

    mock_attachment.save.assert_awaited_once_with(Path(expected_local_path))
    mock_client.files.upload.assert_called_once_with(file=expected_local_path)

    assert mock_logger.info.call_count == expected_log_counts

    # Define the expected calls in order
    expected_calls = [
        call(f"Saved image {expected_local_path}"),
        call("Uploaded unique-file-name.png as files/abc-123"),
    ]

    mock_logger.info.assert_has_calls(expected_calls)
    mock_logger.exception.assert_not_called()
    mock_logger.warning.assert_not_called()

@patch("packages.utilities.file_utils.logger")
@patch(
    "packages.utilities.file_utils.generate_unique_file_name",
    return_value="unique-bad-file.dat",
)
@pytest.mark.asyncio
async def test_handle_attachment_failure_on_save(
    mock_generate_unique_file_name: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Tests the failure scenario.

    Asserts that logger.exception is called exactly once.
    """
    mock_attachment = AsyncMock()
    mock_attachment.filename = "bad_file.dat"
    mock_attachment.content_type = "application/octet-stream"
    mock_attachment.save.side_effect = OSError("Permission denied")

    mock_client = MagicMock()

    expected_file_name = "./temp/unique-bad-file.dat"

    with pytest.raises(HandleAttachmentError) as exc_info:
        await handle_attachment(mock_attachment, mock_client)

    assert isinstance(exc_info.value.__cause__, OSError)
    assert str(exc_info.value)== expected_file_name

    mock_logger.exception.assert_called_once_with(
        "Error when trying to handle attachments.",
    )

    mock_logger.info.assert_not_called()
    mock_logger.error.assert_not_called()
    mock_client.files.upload.assert_not_called()

@patch("packages.utilities.file_utils.read_temp_config", return_value={})
@patch("pathlib.Path.mkdir")
@patch("packages.utilities.file_utils.json.dump")
def test_temp_config_write_to_new_file_and_preserves_falsy_values(
    mock_json_dump: MagicMock,
    mock_mkdir: MagicMock,
    mock_read_temp_config: MagicMock,
) -> None:
    """Tests writing a new config file when none exists.

    Also verifies that values like False and 0 are correctly saved.
    """
    # Act
    save_temp_config(model="model", current_model_index=0, thinking=False)

    # Get the data that was written
    written_data = mock_json_dump.call_args_list[0][0][0]

    expected_data = {
        "model": "model",
        "current_model_index": 0,
        "thinking": False,
    }

    assert written_data == expected_data
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open, read_data=json.dumps(
    {
        "model": "old-model",
        "thinking": True,
    },
))
@patch("packages.utilities.file_utils.json.dump")
def test_temp_config_update_existing_file_and_ignores_none(
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_mkdir: MagicMock,
) -> None:
    """Tests that existing values are preserved and new non-None values are added."""
    # Act
    save_temp_config(model="new_model")

    # Get the data that was written
    written_data = mock_json_dump.call_args_list[0][0][0]

    expected_data = {
        "model": "new_model",
        "thinking": True,
    }

    assert written_data == expected_data
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open, read_data=json.dumps(
    {
        "secret": ["first_secret"],
    },
))
@patch("packages.utilities.file_utils.json.dump")
def test_temp_config_append_secret_to_existing_list(
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_mkdir: MagicMock,
) -> None:
    """Tests writing a new config file when none exists.

    Also verifies that values like False and 0 are correctly saved.
    """
    save_temp_config(secret="new_secret")  # noqa: S106

    # Get the data that was written
    written_data = mock_json_dump.call_args_list[0][0][0]

    expected_data = {
        "secret": ["first_secret", "new_secret"],
    }

    assert written_data == expected_data
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open, read_data=json.dumps(
    {
        "tool_call": [
            {
                "name": "asdf",
                "input": "asdf",
                "output": "asdf",
            },
        ],
    },
))
@patch("packages.utilities.file_utils.json.dump")
def test_temp_config_append_tool_call(
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_mkdir: MagicMock,
) -> None:
    """Tests the append logic for a non-empty 'tool_call' dictionary."""
    save_temp_config(
        tool_call={
            "name": "qwer",
            "input": "qwer",
            "output": "qwer",
        },
    )

    # Get the data that was written
    written_data = mock_json_dump.call_args_list[0][0][0]

    expected_data = {
        "tool_call": [
            {
                "name": "asdf",
                "input": "asdf",
                "output": "asdf",
            },
            {
                "name": "qwer",
                "input": "qwer",
                "output": "qwer",
            },
        ],
    }

    assert written_data == expected_data
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=mock_open, read_data=json.dumps(
    {
        "tool_call": [
            {
                "name": "asdf",
                "input": "asdf",
                "output": "asdf",
            },
        ],
    },
))
@patch("packages.utilities.file_utils.json.dump")
def test_temp_config_reset_tool_call(
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_mkdir: MagicMock,
) -> None:
    """Tests the append logic for a non-empty 'tool_call' dictionary."""
    save_temp_config(tool_call={})

    # Get the data that was written
    written_data = mock_json_dump.call_args_list[0][0][0]
    expected_data = {"tool_call": []}

    assert written_data == expected_data
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_temp_config", return_value={})
@patch("pathlib.Path.open", new_callable=mock_open)
def test_save_temp_config_fail(
    mock_file_open: MagicMock,
    mock_read_temp_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Tests that an exception during file writing is caught and logged."""
    mock_file_open.side_effect = OSError("Permission denied")
    save_temp_config()

    # We assert that the exception was logged as designed.
    mock_logger.exception.assert_called_once()

def test_append_secret_string() -> None:
    """Test _append_secret with a string."""
    result = _append_secret(["existing"], "new_secret")
    assert result == ["existing", "new_secret"]

def test_append_secret_list() -> None:
    """Test _append_secret with a list."""
    result = _append_secret(["existing"], ["new_secret"])
    assert result == ["existing", "new_secret"]


@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_read_temp_config(mock_file_open: MagicMock) -> None:
    """Tests the read_temp_config function."""
    result = read_temp_config()

    mock_file_open.assert_called_once_with("temp/temp_config.json")
    assert result == {}

@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_read_config(mock_file_open: MagicMock) -> None:
    """Tests the read_temp_config function."""
    result = read_config()

    mock_file_open.assert_called_once_with("config.json")
    assert result == {}

@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_success(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test the success scenario where the config is valid."""
    # Arrange: Mock read_config to return a valid dictionary
    mock_read_config.return_value = VALID_CONFIG

    # Act: Call the function
    result = validate_config_files()

    # Assert: The function should return True and not log any errors
    assert result is True
    mock_logger.error.assert_not_called()
    mock_logger.exception.assert_not_called()
    mock_read_config.assert_called_once()


@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_missing_key(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test the scenario where a required key is missing from the config."""
    # Arrange: Create an invalid config by removing a key
    invalid_config = VALID_CONFIG.copy()
    del invalid_config["DiscordToken"]
    mock_read_config.return_value = invalid_config

    # Act: Call the function
    result = validate_config_files()

    # Assert: The function should return False and log a specific error
    assert result is False
    mock_logger.error.assert_called_once()
    # Check that the logged message contains the name of the missing key
    logged_message = mock_logger.error.call_args[0][0]
    assert "DiscordToken" in logged_message
    assert "missing the following required key(s)" in logged_message


@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_incorrect_type(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test the scenario where a key has an incorrect data type."""
    # Arrange: Create an invalid config with the wrong type for 'Temperature'
    invalid_config = VALID_CONFIG.copy()
    invalid_config["Temperature"] = "0.9"  # Should be float, not str
    mock_read_config.return_value = invalid_config

    # Act
    result = validate_config_files()

    # Assert: Should return False and log an error about the invalid key
    assert result is False
    mock_logger.error.assert_called_once()
    logged_message = mock_logger.error.call_args[0][0]
    assert "Temperature" in logged_message
    assert "types are invalid" in logged_message


@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_multiple_issues(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test that multiple missing/invalid keys are reported in one message."""
    # Arrange: Create a config with multiple issues
    invalid_config = VALID_CONFIG.copy()
    del invalid_config["OwnerID"]  # Missing key
    invalid_config["SystemPrompts"] = {}  # Incorrect type
    mock_read_config.return_value = invalid_config

    # Act
    result = validate_config_files()

    # Assert
    assert result is False
    mock_logger.error.assert_called_once()
    logged_message = mock_logger.error.call_args[0][0]
    # Check that both problematic keys are mentioned
    assert "OwnerID" in logged_message
    assert "SystemPrompts" in logged_message


@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_file_not_found(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test the exception handling for FileNotFoundError."""
    # Arrange: Mock read_config to raise FileNotFoundError
    mock_read_config.side_effect = FileNotFoundError

    # Act
    result = validate_config_files()

    # Assert: Should return False and log an exception message for file not found
    assert result is False
    mock_logger.exception.assert_called_once_with(
        "Config file 'config.json' not found. "
        "Please ensure it exists and is correctly named.",
    )


@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_json_decode_error(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test the exception handling for json.JSONDecodeError."""
    # Arrange: Mock read_config to raise a JSONDecodeError
    mock_read_config.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)

    # Act
    result = validate_config_files()

    # Assert: Should return False and log a specific parsing error
    assert result is False
    mock_logger.exception.assert_called_once_with(
        "Config validation failed "
        "because 'config.json' could not be parsed (invalid JSON).",
    )


@patch("packages.utilities.file_utils.logger")
@patch("packages.utilities.file_utils.read_config")
def test_validate_config_files_unexpected_error(
    mock_read_config: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test the generic exception handling for any other error."""
    # Arrange: Mock read_config to raise a generic Exception
    mock_read_config.side_effect = Exception("A wild error appears!")

    # Act
    result = validate_config_files()

    # Assert: Should return False and log a generic unexpected error message
    assert result is False
    mock_logger.exception.assert_called_once_with(
        "An unexpected error occurred during config validation.",
    )

@patch("packages.utilities.file_utils.wave")
def test_save_wave_file_with_explicit_args(mock_wave: MagicMock) -> None:
    """Tests that save_wave_file calls the wave library with correct explicit parameters."""
    # Arrange
    # This mock represents the file handle object returned by `wave.open()`
    # and used within the `with` statement.
    mock_wave_file = mock_wave.open.return_value.__enter__.return_value

    test_filename = "test_output.wav"
    test_pcm = b"\x01\x02\x03\x04"
    test_channels = 2
    test_rate = 44100
    test_sample_width = 3 # Using a non-default value

    # Act
    # Call the function with all arguments specified
    save_wave_file(
        filename=test_filename,
        pcm=test_pcm,
        channels=test_channels,
        rate=test_rate,
        sample_width=test_sample_width,
    )

    # Assert
    # 1. Check that wave.open was called correctly to open the file for writing
    mock_wave.open.assert_called_once_with(test_filename, "wb")

    # 2. Check that all the setup methods on the wave file object were called
    #    with the arguments we provided.
    mock_wave_file.setnchannels.assert_called_once_with(test_channels)
    mock_wave_file.setsampwidth.assert_called_once_with(test_sample_width)
    mock_wave_file.setframerate.assert_called_once_with(test_rate)
    mock_wave_file.writeframes.assert_called_once_with(test_pcm)

@patch("packages.utilities.file_utils.wave")
def test_save_wave_file_with_default_args(mock_wave: MagicMock) -> None:
    """Tests that save_wave_file calls the wave library with default parameters."""
    # Arrange
    mock_wave_file = mock_wave.open.return_value.__enter__.return_value

    test_filename = "default_output.wav"
    test_pcm = b"\xde\xad\xbe\xef"

    # Act
    # Call the function with only the required arguments
    save_wave_file(filename=test_filename, pcm=test_pcm)

    # Assert
    # 1. Check the file open call
    mock_wave.open.assert_called_once_with(test_filename, "wb")

    # 2. Check that the methods were called with the function's default values
    mock_wave_file.setnchannels.assert_called_once_with(1)
    mock_wave_file.setsampwidth.assert_called_once_with(2)
    mock_wave_file.setframerate.assert_called_once_with(24000)
    mock_wave_file.writeframes.assert_called_once_with(test_pcm)
