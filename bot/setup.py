import json
import logging
from pathlib import Path

from google import genai
from google.genai.types import GoogleSearch, HttpOptions, Tool, ToolCodeExecution

from packages.tools.internet import (
    get_wikipedia_page,
    make_get_request,
    search_duckduckgo,
)
from packages.tools.memory import save_memory
from packages.tools.weather import get_weather
from packages.tools.wolfram import wolfram_alpha
from packages.utilities.code_execution import execute_code
# Assuming this is the new flexible save_temp_config
from packages.utilities.file_utils import read_temp_config, save_temp_config

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
    """
    Initializes or updates temp/temp_config.json with default values.
    This ensures all necessary dynamic keys are present on startup.
    """
    temp_config_path = Path("temp/temp_config.json")
    Path("temp").mkdir(parents=True, exist_ok=True) # Ensure temp directory exists

    # Define the default mapping of toolset names to actual tool functions/definitions
    # This should probably be part of your static config.json or a separate file,
    # but for now, I'll keep it here as it was in get_initial_state.
    # Ideally, this should be defined once, maybe in a `tools_map.py` and referenced.
    # For refactoring, I'm sticking to the given structure.
    DEFAULT_TOOLS_MAP = {
        "Default": [
            get_weather,
            make_get_request,
            get_wikipedia_page,
            wolfram_alpha,
            execute_code,
            search_duckduckgo,
            save_memory, # Assumes save_memory is a tool function
        ],
        "Google Search": [Tool(google_search=GoogleSearch())],
        "Code Execution": [Tool(code_execution=ToolCodeExecution())],
        "Nothing": [],
    }

    # Static data from config.json to derive initial temp config values
    system_prompts_from_config = bot_config.get("SystemPrompts", [])
    model_names_from_config = bot_config.get("ModelNames", {})
    tool_set_names_from_config = list(bot_config.get("Tools", DEFAULT_TOOLS_MAP).keys()) # Using DEFAULT_TOOLS_MAP as a fallback for keys

    # Determine initial values
    initial_sys_prompt_index = 0
    initial_system_prompt_data = (
        system_prompts_from_config[initial_sys_prompt_index]["SystemPrompt"]
        if system_prompts_from_config
        else "You are a helpful AI assistant."
    )

    initial_model_id = (
        list(model_names_from_config.keys())[0]
        if model_names_from_config
        else "gemini-1.5-flash-latest" # Fallback if no models defined
    )
    initial_model_index = 0 # Corresponds to the first model in keys()

    initial_active_tools_name = (
        tool_set_names_from_config[0]
        if tool_set_names_from_config
        else "Nothing" # Fallback
    )
    initial_active_tools_index = 0 # Corresponds to the first toolset name

    # Active tool definitions are resolved dynamically from `Tools` in `config.json`
    # which points to DEFAULT_TOOLS_MAP in `prepare_api_config`.
    # So `tool_use` in temp_config should store the *name* of the active toolset, not the object.
    # The `prepare_api_config` function will then use this name to look up the actual tool objects.

    # Read current temp config to merge new defaults
    current_temp_config = {}
    if temp_config_path.exists():
        try:
            with open(temp_config_path, "r", encoding="utf-8") as f:
                current_temp_config = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Corrupted {temp_config_path} found. Reinitializing.")
            current_temp_config = {} # Start fresh if corrupted

    # Define default state for temp_config.json
    default_temp_config = {
        "model": initial_model_id,
        "current_model_index": initial_model_index,
        "system_prompt_data": initial_system_prompt_data,
        "current_sys_prompt_index": initial_sys_prompt_index,
        "current_uwu_status": False,
        "thought": [],
        "secret": "",
        "active_tools_name": initial_active_tools_name,
        "active_tools_index": initial_active_tools_index,
        "thinking": True,
        "thinking_budget": -1,
        "voice_name": "Leda",
    }

    updated_temp_config = {**default_temp_config, **current_temp_config}

    # Save only if there were changes to avoid unnecessary file writes
    if updated_temp_config != current_temp_config:
        with open(temp_config_path, "w", encoding="utf-8") as f:
            json.dump(updated_temp_config, f, indent=4)
        logger.info("Initialized/Updated temp_config.json with default values.")
    else:
        logger.debug("temp_config.json is up to date.")