from discord.ext import commands
import google.generativeai as genai
import discord
import json
import logging

from commands.prompt import prompt
from commands.sync import sync
from commands.get_latest_thought import get_latest_thought

from packages.internet import search_duckduckgo, make_get_request, get_wikipedia_page
from packages.weathermap import get_weather
from packages.wolfram import WolframAlpha
from packages.utils import timeout, hi, execute_code

# Configuration
CONFIG = json.load(open("config.json"))

SYSTEM_PROMPTS = CONFIG["SystemPrompts"]
TOOLS = [search_duckduckgo, get_weather, WolframAlpha, make_get_request, get_wikipedia_page, timeout, hi, execute_code]

genai.configure(api_key=CONFIG['GeminiAPI'])

current_sys_prompt_index = 0
system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
system_prompt_data =  system_prompt['SystemPrompt']

# Model Options and Index
model_options = [
    'gemini-1.5-flash-8b-exp-0827',
    'gemini-1.5-pro-exp-0827',
]

current_model_index = 0
model = model_options[current_model_index]
with open("temp/workaround.json", "w") as TEMP_CONFIG:
    json.dump({"model": model, "system_prompt": system_prompt_data}, TEMP_CONFIG, indent=4)

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# Map internal model names to user-friendly names
model_names = {
    'models/gemini-1.5-flash-8b-exp-0827': 'Gemini 1.5 Flash 8B 0827',
    'models/gemini-1.5-pro-exp-0827': 'Gemini 1.5 Pro Experimental 0827',
}

# Configure logging
logging.basicConfig(level=logging.INFO,  # Set default logging level
                    format='%(asctime)s - %(levelname)s - %(message)s',  # Time - Level Name - message
                    handlers=[  # Add handlers
                        logging.FileHandler("bot.log", encoding='utf-8'),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])

# On start event
@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}. Using {model_options[current_model_index]}')
    friendly_name = model_names['models/' + model_options[current_model_index]]
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))


@client.command(name="toggle_sys")
async def toggle_sys(ctx: commands.Context):
    global model, current_sys_prompt_index, current_model_index
    
    current_model_index = (current_model_index + 1) % len(model_options)
    selected_model = model_options[current_model_index]
    
    current_sys_prompt_index = (current_sys_prompt_index + 1) % len(SYSTEM_PROMPTS)
    system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
    system_prompt_data =  system_prompt['SystemPrompt']
    system_prompt_name = system_prompt['Name']
    
    with open("temp/workaround.json", "w") as TEMP_CONFIG:
        json.dump({"model": selected_model, "system_prompt": system_prompt_data}, TEMP_CONFIG, indent=4)
    
    await ctx.send(f"Using {system_prompt_name}.")

# Toggles to other bots
@client.command(name="toggle")
async def toggle(ctx: commands.Context):
    global current_model_index

    current_model_index = (current_model_index + 1) % len(model_options)
    selected_model = model_options[current_model_index]
    
    system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
    system_prompt_data =  system_prompt['SystemPrompt']
    
    with open("temp/workaround.json", "w") as TEMP_CONFIG:
        json.dump({"model": selected_model, "system_prompt": system_prompt_data}, TEMP_CONFIG, indent=4)

    friendly_name = model_names['models/' + selected_model]
    await ctx.send(f"Switched to {friendly_name}")
    logging.info(f"Switched to {friendly_name}")
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))


@client.command(name="which")
async def which(ctx: commands.Context):
    friendly_name = model_names['models/' + model_options[current_model_index]]
    await ctx.send(f"You are using {friendly_name}")


# Add commands
client.add_command(prompt(TOOLS))
client.add_command(sync)
client.add_command(get_latest_thought)

# Run the bot
client.run(CONFIG['DiscordToken'])