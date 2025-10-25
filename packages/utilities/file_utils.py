from __future__ import annotations

import asyncio
import json
import logging
import time
import wave
from pathlib import Path
from typing import TYPE_CHECKING

from google.genai.types import FileState

from packages.utilities.errors import HandleAttachmentError
from packages.utilities.general_utils import generate_unique_file_name

if TYPE_CHECKING:
    import discord
    from google.genai import Client
    from google.genai.types import File

logger = logging.getLogger(__name__)

def check_for_file_active(uploaded_file: File) -> bool:
    """Check if the uploaded file is active on Google servers."""
    status = uploaded_file.state

    if status == FileState.FAILED:
        msg = "File failed to process!"
        raise RuntimeError(msg)

    return status == FileState.ACTIVE


async def wait_for_file_active(
    uploaded_file_to_check: File,
    timeout: float = 30,
    interval: float = 1,
) -> None:
    """Wait until the uploaded file becomes active on Google servers."""
    start_time = time.monotonic()

    try:
        while not check_for_file_active(uploaded_file_to_check):
            if time.monotonic() - start_time >= timeout:
                logger.warning(
                    f"Timeout while waiting for file {uploaded_file_to_check.name} "
                    f"to become active. Skipping Check.",
                )
                return

            await asyncio.sleep(interval)

    except Exception as e:
        msg = "Error while waiting for file active!"
        logger.exception(msg)
        raise RuntimeError(msg) from e


async def handle_attachment(
        attachment: discord.Attachment,
        client: Client,
) -> tuple[list[str], list[File]]:
    """Handle a discord.Attachment and uploads them to Google."""
    file_name = ""
    try:
        file_extension = attachment.filename.split(".")[-1]
        unique_file_name = generate_unique_file_name(file_extension)
        file_name = f"./temp/{unique_file_name}"

        await attachment.save(Path(file_name))
        logger.info(f"Saved {attachment.content_type.split('/')[0]} {file_name}")

        file_names = []
        uploaded_files = []

        file_names.append(file_name)
        uploaded_file = await asyncio.to_thread(client.files.upload, file=file_name)
        uploaded_files.append(uploaded_file)

        logger.info(f"Uploaded {uploaded_file.display_name} as {uploaded_file.name}")

        return file_names, uploaded_files
    except Exception as e:
        logger.exception("Error when trying to handle attachments.")
        raise HandleAttachmentError(file_name) from e


def save_temp_config(
    model: str | None = None,
    current_model_index: int | None = None,
    system_prompt_data: str | None = None,
    current_sys_prompt_index: int | None = None,
    current_uwu_status: bool | None = None,
    thought: list | None = None,
    secret: list | str | None = None,
    tool_call: dict | None = None,
    active_tools_name: str | None = None,
    active_tools_index: int | None = None,
    thinking: bool | None = None,
    thinking_budget: int | None = None,
    voice_name: str | None = None,
    system_prompt_name: str | None = None,
) -> None:
    """Saves the current configuration to temp_config.json, preserving existing keys.

    This function updates only the keys for which a non-None argument is provided.
    It has special handling for 'secret' and 'tool_call'.

    - 'secret': The new value is appended to the existing list of secrets.
    - 'tool_call': A new tool call dictionary is appended to the 'tool_call' list.
                   Providing an empty dictionary `{}` will clear the entire list.
    """
    temp_config_path = Path("temp/temp_config.json")
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)

    # Read the current config, or start with an empty dict if it's invalid
    config = read_temp_config()

    # Create a dictionary of simple updates, filtering out None values
    updates = {
        "model": model,
        "current_model_index": current_model_index,
        "system_prompt_data": system_prompt_data,
        "current_sys_prompt_index": current_sys_prompt_index,
        "current_uwu_status": current_uwu_status,
        "thought": thought,
        "active_tools_name": active_tools_name,
        "active_tools_index": active_tools_index,
        "thinking": thinking,
        "thinking_budget": thinking_budget,
        "voice_name": voice_name,
        "system_prompt_name": system_prompt_name,
    }

    # Filter out None values and update the configuration
    # This handles False and 0 values correctly
    filtered_updates = {k: v for k, v in updates.items() if v is not None}
    config.update(filtered_updates)

    # Special handling for 'secret' to append instead of overwrite
    if secret is not None:
        existing_secrets = config.get("secret", [])
        config["secret"] = _append_secret(existing_secrets, secret)

    # Special handling for 'tool_call' to append to 'tool_call' list
    # This implements the requested logic.
    if tool_call is not None:
        # If tool_call is a non-empty dictionary, append it.
        if tool_call:  # Pythonic way to check for non-empty dict
            existing_tool_call = config.get("tool_call", [])
            existing_tool_call.append(tool_call)
            config["tool_call"] = existing_tool_call
        # If tool_call is an empty dictionary `{}`, clear the list.
        else:
            config["tool_call"] = []

    # Write the updated config back to the file
    try:
        with temp_config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception:
        logger.exception("Failed to save temp_config.json")


def _append_secret(existing_secrets: list, secret: list | str) -> list:
    if isinstance(secret, list):
        return existing_secrets + secret
    return [*existing_secrets, secret]


def read_temp_config() -> dict:
    """Reads the configuration from temp/temp_config.json.

    Returns:
        dict: A dictionary containing the configuration, or an empty dictionary
              if the file doesn't exist or contains invalid JSON.
    """
    temp_config_path = "temp/temp_config.json"
    with open(temp_config_path) as f:
        return json.load(f)


def read_config() -> dict[str, str | float]:
    """Load the configuration from config.json."""
    with open("config.json") as f:
        return json.load(f)


def validate_config_files() -> bool:
    """Validates if the required keys are present in the config file.

    Checks for the existence of essential configuration keys. If the file
    is missing or if any required key is not found in the loaded config,
    it logs an error detailing the issue.

    Returns:
        True if the config file exists and contains all required keys
        and their types are correct.
        Otherwise, False.
    """
    required_keys = {
        "GeminiAPIkey": str,
        "DiscordToken": str,
        "OwnerID": str,
        "ModelNames": dict,
        "SystemPrompts": list,
        "HarmBlockThreshold": str,
        "Temperature": float,
    }

    try:
        config = read_config()

        missing_keys = []
        for key, value in required_keys.items():
            if key not in config or not isinstance(config[key], value):
                missing_keys.append(key)

        if missing_keys:
            # Report all missing keys at once
            logger.error(
                f"Config validation failed. File 'config.json' is missing "
                f"the following required key(s) or the types "
                f"are invalid: {', '.join(missing_keys)}",
            )
            return False
        return True

    except FileNotFoundError:
        # Log specifically that the file is missing
        logger.exception(
            "Config file 'config.json' not found. "
            "Please ensure it exists and is correctly named.",
        )
        return False
    except json.JSONDecodeError:
        logger.exception(
            "Config validation failed "
            "because 'config.json' could not be parsed (invalid JSON).",
        )
        return False
    except Exception:
        logger.exception("An unexpected error occurred during config validation.")
        return False


def save_wave_file(
    filename: str,
    pcm: bytes,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
) -> None:
    """Saves PCM audio data to a WAVE file.

    Args:
        filename: The name of the file to save the audio to.
        pcm: The PCM audio data as bytes.
        channels: The number of audio channels (e.g., 1 for mono, 2 for stereo).
                  Defaults to 1.
        rate: The sampling rate in Hz (frames per second). Defaults to 2400.
        sample_width: The sample width in bytes (e.g., 2 for 16-bit audio).
                      Defaults to 2.
    """
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
