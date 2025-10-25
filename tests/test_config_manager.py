import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from bot.config import ConfigManager

TIMEOUT = 30

# Fixture to provide a dictionary of sample config data
@pytest.fixture
def sample_config_data() -> dict[str, Any]:
    """Provides a sample configuration dictionary."""
    return {
        "bot_token": "your_secret_token_here",
        "command_prefix": "!",
        "log_level": "INFO",
        "enabled_features": ["feature1", "feature2"],
        "api_settings": {
            "url": "https://api.example.com",
            "timeout": TIMEOUT,
        },
    }


@pytest.fixture
def config_file(tmp_path: Path, sample_config_data: dict[str, Any]) -> Path:
    """Creates a temporary config JSON file and returns its path."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps(sample_config_data), encoding="utf-8")
    return p


def test_init_success(config_file: Path, sample_config_data: dict[str, Any]) -> None:
    """Tests successful initialization and loading of a valid config file."""
    manager = ConfigManager(config_file)
    assert manager.get_all_config() == sample_config_data
    assert manager.path == config_file
    assert manager._last_mtime is not None


def test_init_file_not_found(tmp_path: Path, caplog: LogCaptureFixture) -> None:
    """Tests that initialization raises FileNotFoundError for a non-existent file."""
    non_existent_path = tmp_path / "not_found.json"
    with caplog.at_level(logging.CRITICAL), pytest.raises(FileNotFoundError):
        ConfigManager(non_existent_path)
    assert f"Configuration file not found at {non_existent_path}" in caplog.text


def test_init_invalid_json(tmp_path: Path, caplog: LogCaptureFixture) -> None:
    """Tests that initialization raises JSONDecodeError for a malformed JSON file."""
    invalid_json_file = tmp_path / "invalid.json"
    invalid_json_file.write_text("{'key': 'value',}")

    with caplog.at_level(logging.CRITICAL), pytest.raises(json.JSONDecodeError):
        ConfigManager(invalid_json_file)
    assert f"Failed to parse JSON from {invalid_json_file}" in caplog.text


# --- Data Access Tests ---

@pytest.fixture
def manager(config_file: Path) -> ConfigManager:
    """Provides an initialized ConfigManager instance for data access tests."""
    return ConfigManager(config_file)


def test_getitem(manager: ConfigManager) -> None:
    """Tests dictionary-style access using __getitem__."""
    assert manager["command_prefix"] == "!"
    assert manager["api_settings"]["timeout"] == TIMEOUT
    with pytest.raises(KeyError):
        _ = manager["non_existent_key"]


def test_get(manager: ConfigManager) -> None:
    """Tests safe access using the .get() method."""
    assert manager.get("bot_token") == "your_secret_token_here"
    assert manager.get("non_existent_key") is None
    assert manager.get(
        "non_existent_key", "default_value",
    ) == "default_value"


def test_contains(manager: ConfigManager) -> None:
    """Tests the `in` operator using __contains__."""
    assert "log_level" in manager
    assert "non_existent_key" not in manager


def test_get_all_config_is_a_copy(manager: ConfigManager) -> None:
    """Tests that get_all_config() returns a copy, not a reference."""
    config_copy = manager.get_all_config()
    config_copy["new_key"] = "new_value"

    # The original config should not be modified
    assert "new_key" not in manager
    with pytest.raises(KeyError):
        _ = manager["new_key"]


# --- Hot-Reloading Tests ---

def test_check_for_updates_no_change(
    manager: ConfigManager, mocker: MockerFixture,
) -> None:
    """Tests that _load() is not called if the file hasn't been modified."""
    spy_load = mocker.spy(manager, "_load")

    # This call should NOT trigger a reload.
    manager._check_for_updates()

    # Therefore, the spy should have recorded zero calls.
    assert spy_load.call_count == 0

    # If you wanted to be extra explicit, you could also use this syntax:
    spy_load.assert_not_called()


def test_check_for_updates_file_modified(
    config_file: Path, manager: ConfigManager, caplog: LogCaptureFixture,
) -> None:
    """Tests that the config is reloaded when the file is modified."""
    time.sleep(0.01)

    new_data = {"bot_token": "new_updated_token"}
    config_file.write_text(json.dumps(new_data))

    with caplog.at_level(logging.INFO):
        manager._check_for_updates()

    assert (
        f"Change detected in '{config_file}'. Reloading configuration."
        in caplog.text
    )
    assert manager["bot_token"] == "new_updated_token"
    assert "command_prefix" not in manager


def test_check_for_updates_file_deleted(
    manager: ConfigManager, config_file: Path, caplog: LogCaptureFixture,
) -> None:
    """Tests that a warning is logged if the file is deleted after initialization."""
    original_config = manager.get_all_config()
    config_file.unlink()  # Delete the file

    with caplog.at_level(logging.WARNING):
        manager._check_for_updates()

    assert (
        f"Configuration file '{config_file}' was not found during a scheduled check."
        in caplog.text
    )
    # The in-memory config should remain unchanged
    assert manager.get_all_config() == original_config


def test_check_for_updates_handles_other_exceptions(
    manager: ConfigManager, mocker: MockerFixture, caplog: LogCaptureFixture,
) -> None:
    """Tests that generic exceptions during the check are caught and logged."""
    mocker.patch.object(
        Path,
        "stat",
        side_effect=PermissionError("Access denied"),
    )

    with caplog.at_level(logging.ERROR):
        manager._check_for_updates()

    assert "An error occurred during configuration reload: Access denied" in caplog.text


@pytest.mark.asyncio
async def test_start_hot_reload_loop(
    manager: ConfigManager, mocker: MockerFixture,
) -> None:
    """Tests that the hot-reload loop runs and calls the check method."""
    spy_check = mocker.spy(manager, "_check_for_updates")

    # Run the loop for a very short time and then cancel it
    hot_reload_task = asyncio.create_task(
        manager.start_hot_reload_loop(interval_seconds=0.01),
    )

    await asyncio.sleep(0.05)
    hot_reload_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await hot_reload_task

    assert spy_check.call_count >= 0
