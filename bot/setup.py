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


def setup_logging() -> None:
    """Configure logging to file and console."""
    # Make folder if not exist
    Path("logs").mkdir(exist_ok=True)

    # Define log format
    log_format = (
        "%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s"
    )
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    logger.info("Set up logging.")

def setup_gemini(api_key: str, api_version: str = "v1alpha") -> genai.Client:
    """Configures the Google Gemini API client."""
    return genai.Client(
        api_key=api_key,
        http_options=HttpOptions(api_version=api_version),
    )

def get_initial_state(config: dict) -> dict:
    """Gets the initial state for the bot (model, system prompt, etc.)."""
    logger = logging.getLogger(__name__)
    temp_config_path = "temp/temp_config.json"
    try:
        Path(temp_config_path).unlink()
        logger.info("Removed temp_config.json")
    except FileNotFoundError:
        logger.info("temp_config.json not found, no need to remove.")
    except OSError:
        logger.exception("Error removing temp_config.json.")

    system_prompts = config["SystemPrompts"]
    model_options = list(config["ModelNames"])
    model_clean_names = dict(config["ModelNames"].items())

    tools = {
        "Default": [
            get_weather,
            make_get_request,
            get_wikipedia_page,
            wolfram_alpha,
            execute_code,
            search_duckduckgo,
            save_memory,
        ],
        "Google Search": [Tool(google_search=GoogleSearch())],
        "Code Execution": [Tool(code_execution=ToolCodeExecution())],
        "Nothing": [],
    }

    current_sys_prompt_index = 0
    system_prompt_data = system_prompts[current_sys_prompt_index]["SystemPrompt"]
    current_model_index = 0
    model = model_options[current_model_index]
    current_uwu_status = False
    active_tools_index = 0
    tool_names = list(tools.keys())
    active_tools = tools[tool_names[active_tools_index]]

    if not Path("temp").is_dir():
        Path("temp").mkdir(parents=True)

    with open(temp_config_path, "w") as f:
        json.dump(
            {
                "model": model,
                "system_prompt": system_prompt_data,
                "uwu": current_uwu_status,
                "thought": "",
                "secret": [],
                "tools_history": [],
                "thinking": True,
                "thinking_budget": -1, # -1 (NOT 0) means auto thinking length
            }, f)

    return {
        "system_prompts": system_prompts,
        "model_options": model_options,
        "current_sys_prompt_index": current_sys_prompt_index,
        "system_prompt_data": system_prompt_data,
        "current_model_index": current_model_index,
        "model": model,
        "current_uwu_status": current_uwu_status,
        "tools": tools,
        "active_tools": active_tools,
        "active_tools_index": active_tools_index,
        "model_clean_names": model_clean_names,
    }

