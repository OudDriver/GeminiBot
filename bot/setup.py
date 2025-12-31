from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from google import genai
from google.genai.types import HttpOptions, Tool, GoogleSearch, ToolCodeExecution, UrlContext

from packages.tools.genius import get_lyrics
from packages.tools.internet import make_get_request, get_wikipedia_page, search_duckduckgo
from packages.tools.memory import save_memory
from packages.tools.weather import get_weather
from packages.tools.wolfram import wolfram_alpha
from packages.tools.code_execution import execute_code

logger = logging.getLogger(__name__)

def setup_logging() -> None:
    """Configure logging to file and console."""
    Path("logs").mkdir(exist_ok=True)
    log_format = (
        "%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s"
    )
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    for handler in root_logger.handlers[:]: # Clear existing handlers
        root_logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)

    logger.info("Set up logging.")

def setup_gemini(api_key: str, api_version: str = "v1alpha") -> genai.Client:
    """Configures the Google Gemini API client."""
    return genai.Client(
        api_key=api_key,
        http_options=HttpOptions(api_version=api_version),
    )

def initialize_temp_config(bot_config: dict) -> None:
    """Initializes or updates temp/temp_config.json with default values.

    This ensures all necessary dynamic keys are present on startup.
    """
    temp_config_path = Path("temp/temp_config.json")
    Path("temp").mkdir(parents=True, exist_ok=True) # Ensure temp directory exists

    system_prompts_from_config = bot_config.get("SystemPrompts", [])
    model_names_from_config = bot_config.get("ModelNames", {})
    tool_set_names_from_config = list(bot_config.get("Tools", DEFAULT_TOOLS_MAP).keys())

    initial_sys_prompt_index = 0
    initial_system_prompt_data = system_prompts_from_config[
        initial_sys_prompt_index
    ]["SystemPrompt"]
    initial_system_prompt_name = system_prompts_from_config[
        initial_sys_prompt_index
    ]["Name"]

    initial_model_id = next(iter(model_names_from_config.keys()))
    initial_model_index = 0

    initial_active_tools_name = tool_set_names_from_config[0]
    initial_active_tools_index = 0 # Corresponds to the first toolset name

    # Define default state for temp_config.json
    default_temp_config = {
        "model": initial_model_id,
        "current_model_index": initial_model_index,
        "system_prompt_data": initial_system_prompt_data,
        "system_prompt_name": initial_system_prompt_name,
        "current_sys_prompt_index": initial_sys_prompt_index,
        "current_uwu_status": False,
        "thought": [],
        "secret": [],
        "active_tools_name": initial_active_tools_name,
        "active_tools_index": initial_active_tools_index,
        "thinking": True,
        "thinking_budget": -1,
        "voice_name": "Leda",
        "tool_call": [],
    }

    if Path(temp_config_path).exists():
        Path(temp_config_path).unlink()

    with open(temp_config_path, "w", encoding="utf-8") as f:
        json.dump(default_temp_config, f, indent=4)
        logger.info("Overwritten temp_config.json.")


DEFAULT_TOOLS_MAP = {
    "Default": [
        get_weather,
        make_get_request,
        get_wikipedia_page,
        wolfram_alpha,
        execute_code,
        search_duckduckgo,
        save_memory,
        get_lyrics,
    ],
    "Google Search & Code Execution": [
        Tool(google_search=GoogleSearch()),
        Tool(code_execution=ToolCodeExecution()),
    ],
    "Google Search & URL Context": [
        Tool(google_search=GoogleSearch()),
        Tool(url_context=UrlContext()),
    ],
    "Nothing": [],
}
