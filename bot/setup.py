
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
    with open("config.json", "r") as f:
        return json.load(f)

def setup_logging():
    """Configures logging to file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("bot.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

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

    temp_config_path = "temp/temp_config.json"
    if os.path.exists(temp_config_path):
        try:
            with open(temp_config_path, "r") as f:
                temp_config = json.load(f)
                
                current_model_index = model_options.index(temp_config['model'])
                model = temp_config["model"]

                for i in range(len(system_prompts)):
                    if system_prompts[i]["SystemPrompt"] == temp_config["system_prompt"]:
                        current_sys_prompt_index = i

                system_prompt_data = temp_config["system_prompt"]
                current_uwu_status = temp_config["uwu"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
            logging.warning(f"Error loading temp_config.json: {e}. Using default values.")
            
            if not os.path.isdir("./temp"):
                os.makedirs("./temp")

            with open(temp_config_path, "w") as f:
                json.dump({"model": model, "system_prompt": system_prompt_data, "uwu": current_uwu_status, "thought": "", "secret": []}, f)
    else:
        if not os.path.isdir("./temp"):
            os.makedirs("./temp")

        with open(temp_config_path, "w") as f:
            json.dump({"model": model, "system_prompt": system_prompt_data, "uwu": current_uwu_status, "thought": "", "secret": []}, f)


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
        "active_tools_index": active_tools_index
    }

