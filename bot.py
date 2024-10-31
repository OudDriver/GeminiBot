from discord.ext import commands
import google.generativeai as genai
import discord
import json
import logging

from commands.prompt import prompt
from commands.sync import sync
from commands.thought import thought, secret

from packages.internet import search_duckduckgo, make_get_request, get_wikipedia_page
from packages.weathermap import get_weather
from packages.wolfram import wolfram_alpha
from packages.utils import timeout, hi, execute_code

# Config File
CONFIG = json.load(open("config.json"))

# System Prompt and Tools for the bot
SYSTEM_PROMPTS = CONFIG["SystemPrompts"]
TOOLS = [search_duckduckgo, get_weather, wolfram_alpha, make_get_request, get_wikipedia_page, timeout, hi, execute_code]

genai.configure(api_key=CONFIG['GeminiAPI'])

# System Prompt Handling
current_sys_prompt_index = 0
system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
system_prompt_data =  system_prompt['SystemPrompt']

# Model Options and Index
model_options = [key for key in CONFIG["ModelNames"]]

# Saving temporary configurations to temp/workaround.json to transfer to prompt.py
current_model_index = 0
model = model_options[current_model_index]
with open("temp/workaround.json", "w") as TEMP_CONFIG:
    TEMP_CONFIG.write(json.dumps({"model": model, "system_prompt": system_prompt_data}, indent=4))

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

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
    friendly_name = CONFIG["ModelNames"][model_options[current_model_index]]
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))

# Toggle system prompt incrementally
@client.command(name="toggle_sys")
async def toggle_sys(ctx: commands.Context):
    global model, current_sys_prompt_index, current_model_index
    
    # Gets the current model
    current_model_index = (current_model_index + 1) % len(model_options)
    selected_model = model_options[current_model_index]
    
    # Gets the system prompt using the index
    current_sys_prompt_index = (current_sys_prompt_index + 1) % len(SYSTEM_PROMPTS)
    changed_system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
    changed_system_prompt_data =  changed_system_prompt['SystemPrompt']
    system_prompt_name = changed_system_prompt['Name']
    
    # Saves the info to the file
    with open("temp/workaround.json", "w") as SYS_TEMP_CONFIG:
        SYS_TEMP_CONFIG.write(json.dumps({"model": selected_model, "system_prompt": changed_system_prompt_data}, indent=4))
    
    await ctx.send(f"Using {system_prompt_name}.")

# Toggles to other bots incrementally
@client.command(name="toggle")
async def toggle(ctx: commands.Context):
    global current_model_index

    # Gets the model using the index
    current_model_index = (current_model_index + 1) % len(model_options)
    selected_model = model_options[current_model_index]
    
    # Gets the system prompt
    current_system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
    current_system_prompt_data =  current_system_prompt['SystemPrompt']
    
    # Saves the info to the file
    with open("temp/workaround.json", "w") as SYS_TEMP_CONFIG:
        SYS_TEMP_CONFIG.write(json.dumps({"model": selected_model, "system_prompt": current_system_prompt_data}, indent=4))

    friendly_name = CONFIG["ModelNames"][selected_model]
    logging.info(f"Switched to {friendly_name}")
    
    await ctx.send(f"Switched to {friendly_name}")

    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))


# Shows the models you are using
@client.command(name="which")
async def which(ctx: commands.Context):
    friendly_name = CONFIG["ModelNames"][model_options[current_model_index]]
    await ctx.send(f"You are using {friendly_name}")


# Add commands
client.add_command(prompt(TOOLS))
client.add_command(sync)
client.add_command(thought)
client.add_command(secret)

# Run the bot
client.run(CONFIG['DiscordToken'])