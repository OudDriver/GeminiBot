from discord.ext import commands
import google.generativeai as genai
import discord
import json
import logging

from commands.prompt import prompt
from commands.sync import sync

from packages.duckduckgo import search_duckduckgo
from packages.weathermap import get_weather
from packages.wolfram import wolfram

# Configuration
with open('config.json') as f:
    config = json.loads(f.read())

# CONSTANTS and variables
SYSTEM_PROMPT = "You are a helpful AI assistant."

TOOLS = [search_duckduckgo, get_weather, wolfram]

genai.configure(api_key=config['GeminiAPI'])

# Model Options and Index
model_options = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-8b-exp-0827',
    'gemini-1.5-pro',
    'gemini-1.5-pro-exp-0827',
    'gemma-2-27b-it'
]

current_model_index = 0
model = genai.GenerativeModel(model_options[current_model_index], tools=TOOLS, system_instruction=SYSTEM_PROMPT)

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# Map internal model names to user-friendly names
model_names = {
    'models/gemini-1.5-flash': 'Gemini 1.5 Flash',
    'models/gemini-1.5-flash-8b-exp-0827': 'Gemini 1.5 Flash 8B 0827',
    'models/gemini-1.5-pro': 'Gemini 1.5 Pro',
    'models/gemini-1.5-pro-exp-0827': 'Gemini 1.5 Pro Experimental 0827',
    'models/gemma-2-27b-it': 'Gemma 2 27b'
}

# Configure logging
logging.basicConfig(level=logging.INFO,  # Set default logging level
                    format='%(asctime)s - %(levelname)s - %(message)s',  # Time - Level Name - message
                    handlers=[  # Add handlers
                        logging.FileHandler("bot.log"),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])


# On start event
@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}. Using {model.model_name}')
    friendly_name = model_names[model.model_name]
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))


# Toggles to other bots
@client.command(name="toggle")
async def toggle(ctx: commands.Context):
    global model, current_model_index

    current_model_index = (current_model_index + 1) % len(model_options)
    selected_model = model_options[current_model_index]

    model = genai.GenerativeModel(selected_model, tools=TOOLS, system_instruction=SYSTEM_PROMPT)

    friendly_name = model_names['models/' + selected_model]
    await ctx.send(f"Switched to {friendly_name}")
    logging.info(f"Switched to {friendly_name}")
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))


@client.command(name="which")
async def which(ctx: commands.Context):
    """
    See which model you are using. 
    """
    friendly_name = model_names['models/' + model.model_name]
    await ctx.send(f"You are using {friendly_name}")


# Add commands
client.add_command(prompt(model))
client.add_command(sync)

# Run the bot
client.run(config['DiscordToken'])