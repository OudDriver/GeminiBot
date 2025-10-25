import json
import logging
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from _pytest.capture import CaptureFixture

from bot.setup import (
    DEFAULT_TOOLS_MAP,
    initialize_temp_config,
    setup_gemini,
    setup_logging,
)


# Fixture to run tests in an isolated temporary directory
@pytest.fixture
def isolated_tmp_dir(tmp_path: Path) -> Generator[Path, Any, None]:
    """Creates a temporary directory and changes the current working directory to it."""
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def sample_bot_config() -> dict:
    """Provides a sample bot_config dictionary for testing."""
    return {
        "SystemPrompts": [
            {"Name": "Prompt A", "SystemPrompt": "You are assistant A."},
            {"Name": "Prompt B", "SystemPrompt": "You are assistant B."},
        ],
        "ModelNames": {
            "test-model-1": "Test Model 1",
            "test-model-2": "Test Model 2",
        },
        "Tools": {
            "FirstToolSet": [],
            "SecondToolSet": [],
        },
    }

def test_setup_logging_creates_dir_and_file(isolated_tmp_dir: Path) -> None:
    """Verify that 'logs' directory and 'bot.log' file are created."""
    logs_dir = isolated_tmp_dir / "logs"
    log_file = logs_dir / "bot.log"
    assert not logs_dir.exists()
    setup_logging()
    assert logs_dir.is_dir()
    assert log_file.is_file()

def test_setup_logging_clears_existing_handlers(isolated_tmp_dir: Path) -> None:
    """Verify that pre-existing handlers on the root logger are removed."""
    # The function adds 2 handlers (File and Stream)
    expected_handlers = 2

    root_logger = logging.getLogger()
    dummy_handler = logging.NullHandler()
    root_logger.addHandler(dummy_handler)

    assert dummy_handler in root_logger.handlers
    setup_logging()
    assert dummy_handler not in root_logger.handlers

    assert len(root_logger.handlers) == expected_handlers

def test_setup_logging_adds_correct_handlers(isolated_tmp_dir: Path) -> None:
    """Verify that a FileHandler and StreamHandler are added."""
    # Reset logger state before test
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    setup_logging()
    assert len(root_logger.handlers) == 2
    handler_types = [type(h) for h in root_logger.handlers]
    assert logging.FileHandler in handler_types
    assert logging.StreamHandler in handler_types

def test_setup_logging_logs_setup_message(
    isolated_tmp_dir: Path,
    capsys: CaptureFixture,
) -> None:
    """Verify the confirmation message is logged by capturing stderr."""
    setup_logging()
    captured = capsys.readouterr()
    # The StreamHandler logs to stderr by default.
    assert "Set up logging." in captured.err

@patch("bot.setup.genai.Client")
@patch("bot.setup.HttpOptions")
def test_setup_gemini(
    mock_http_options: MagicMock,
    mock_genai_client: MagicMock,
) -> None:
    """Verify that the genai Client is instantiated with the correct parameters."""
    api_key = "test-api-key"
    api_version = "v1beta"

    # Configure the mock HttpOptions to return a mock object
    mock_options_instance = MagicMock()
    mock_http_options.return_value = mock_options_instance

    # Call the function under test
    client = setup_gemini(api_key=api_key, api_version=api_version)

    # Assert that HttpOptions was called correctly
    mock_http_options.assert_called_once_with(api_version=api_version)

    # Assert that genai.Client was called correctly
    mock_genai_client.assert_called_once_with(
        api_key=api_key,
        http_options=mock_options_instance,
    )

    # Assert that the function returns the created client instance
    assert client == mock_genai_client.return_value

def test_creates_file_and_dir_from_scratch(
    isolated_tmp_dir: Path,
    sample_bot_config: dict,
) -> None:
    """Verify it creates temp/temp_config.json correctly when nothing exists."""
    temp_config_path = isolated_tmp_dir / "temp" / "temp_config.json"
    assert not temp_config_path.exists()
    initialize_temp_config(sample_bot_config)
    assert temp_config_path.is_file()
    with temp_config_path.open() as f:
        data = json.load(f)

    assert data["model"] == "test-model-1"
    assert data["system_prompt_name"] == "Prompt A"
    assert data["system_prompt_data"] == "You are assistant A."
    assert data["active_tools_name"] == "FirstToolSet"
    assert data["current_uwu_status"] is False

def test_overwrites_existing_file(
    isolated_tmp_dir: Path,
    sample_bot_config: dict,
) -> None:
    """Verify that an existing temp_config.json is completely overwritten."""
    temp_dir = isolated_tmp_dir / "temp"
    temp_dir.mkdir()
    temp_config_path = temp_dir / "temp_config.json"

    old_data = {"model": "old-model", "current_uwu_status": True}
    temp_config_path.write_text(json.dumps(old_data))
    initialize_temp_config(sample_bot_config)
    with temp_config_path.open() as f:
        new_data = json.load(f)

    # Verify old data is gone and new data is present
    assert new_data["model"] == "test-model-1"
    assert new_data["current_uwu_status"] is False
    assert "system_prompt_name" in new_data

def test_uses_default_tools_map_if_key_missing(
    isolated_tmp_dir: Path,
    sample_bot_config: dict,
) -> None:
    """Verify it falls back to DEFAULT_TOOLS_MAP if 'Tools' is not in config."""
    # Create a config that is missing the "Tools" key
    config_without_tools = sample_bot_config.copy()
    del config_without_tools["Tools"]
    initialize_temp_config(config_without_tools)
    temp_config_path = isolated_tmp_dir / "temp" / "temp_config.json"
    with temp_config_path.open() as f:
        data = json.load(f)
    # The first key from the default map should be used
    expected_first_tool_name = next(iter(DEFAULT_TOOLS_MAP.keys()))
    assert data["active_tools_name"] == expected_first_tool_name
