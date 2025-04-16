import json
import logging
import os

from google import genai
from google.genai.types import GoogleSearch, ToolCodeExecution, Tool

from packages.internet import search_duckduckgo, make_get_request, get_wikipedia_page
from packages.weather import get_weather
from packages.wolfram import wolfram_alpha
from packages.utils import execute_code
from packages.memory import save_memory

def load_config():
    """Loads the configuration from config.json."""
    with open("config.json") as f:
        return json.load(f)

def setup_logging():
    """Configures logging to file and console."""
    # Define log format
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'
    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    try:
        file_handler = logging.FileHandler("bot.log", encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file logging: {e}") # Basic error print if file handler fails

    # --- Console (Stream) Handler ---
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    logging.info("Set up logging.")

def setup_gemini(api_key):
    """Configures the Google Gemini API client."""
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})

def get_initial_state(config):
    """Gets the initial state for the bot (model, system prompt, etc.)."""

    temp_config_path = "temp/temp_config.json"
    try:
        os.remove(temp_config_path)
        logging.info("Removed temp_config.json")  
    except FileNotFoundError:
        logging.info("temp_config.json not found, no need to remove.") 
    except OSError as e:
        logging.error(f"Error removing temp_config.json: {e}")  

    system_prompts = config["SystemPrompts"]
    model_options = [key for key in config["ModelNames"]]
    model_clean_names = {}

    for key, value in config["ModelNames"].items():
        model_clean_names[key] = value
    
    tools = {
        "Default": [get_weather, make_get_request, get_wikipedia_page, wolfram_alpha, execute_code, search_duckduckgo, save_memory],
        "Google Search": [Tool(google_search=GoogleSearch())],
        "Code Execution": [Tool(code_execution=ToolCodeExecution())]
    }

    current_sys_prompt_index = 0
    system_prompt_data = system_prompts[current_sys_prompt_index]['SystemPrompt']
    current_model_index = 0
    model = model_options[current_model_index]
    current_uwu_status = False
    active_tools_index = 0
    tool_names = list(tools.keys())
    active_tools = tools[tool_names[active_tools_index]]

    if not os.path.isdir("./temp"):
        os.makedirs("./temp")

    with open(temp_config_path, "w") as f:
        json.dump({"model": model, "system_prompt": system_prompt_data, "uwu": current_uwu_status, "thought": "", "secret": [], "tools_history": []}, f)

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
        "model_clean_names": model_clean_names
    }

