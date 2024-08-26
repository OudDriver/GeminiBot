from discord.ext import commands
import google.generativeai as genai
import discord
import json
import logging

from commands.prompt import prompt
from commands.sync import sync

# Configuration
with open('config.json') as f:
    config = json.loads(f.read())
    
# CONSTANTS and variables
SYSTEM_PROMPT = "You are a friendly, fun, and knowledgeable multimodal AI assistant. You are connected to Discord. If a user asks about topics you don't know the answer to, politely inform them that you cannot answer on those questions. If a user becomes hostile or uses inappropriate language, maintain a calm and professional demeanor. When generating stories or poems, feel free to use figurative language, such as metaphors, similes, and personification, to make your writing more vivid and engaging. Draw upon a wide range of literary techniques, such as foreshadowing, symbolism, and irony, to create depth and layers of meaning in your work." # Instructions for the bot

TOOLS = 'code_execution' # Code execution for the bot so the bot don't mess up 12079834709812078943 + 32649719732147689

genai.configure(api_key=config['GeminiAPI']) # Configures Gemini with my API key
model = genai.GenerativeModel('gemini-1.5-flash', tools=TOOLS, system_instruction=SYSTEM_PROMPT) # Sets up Gemini with Code Execution and my system prompt

# Discord Bot Setup
intents = discord.Intents.default() # Loads default intents
intents.message_content = True # Lets bot see messages
client = commands.Bot(command_prefix='!', intents=intents) # Adds the prefix "!" for commands. example: !prompt Hello

# Map internal model names to user-friendly names
model_names = {
    'models/gemini-1.5-flash': 'Gemini 1.5 Flash',
    'models/gemini-1.5-pro': 'Gemini 1.5 Pro',
    'models/gemini-1.5-pro-exp-0801': 'Gemini 1.5 Pro 0801',
    'models/gemma-2-27b-it': 'Gemma 2 27b'
} 

# Configure logging
logging.basicConfig(level=logging.INFO, # Set default logging level
                    format='%(asctime)s - %(levelname)s - %(message)s', # Time - Level Name - message
                    handlers=[ # Add handlers
                        logging.FileHandler("bot.log"),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])

# On start event 
@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}. Using {model.model_name}') # Print stuff so I know the bot is working 
    friendly_name = model_names[model.model_name] # Selects the correct friendly name
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}')) # Change the status to the friendly bot name

# Toggles to other bots
@client.command(name="toggle")
async def toggle(ctx: commands.Context):
    """
    Toggles between Gemini 1.5 Pro, Gemini 1.5 Flash, and Gemma 2 27b. 
    """
    global model
    
    # Some if events to change to the correct bots
    if model.model_name == "models/gemini-1.5-flash":
        model = genai.GenerativeModel('gemini-1.5-pro', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    elif model.model_name == "models/gemini-1.5-pro":
        model = genai.GenerativeModel('gemini-1.5-pro-exp-0801', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    elif model.model_name == "models/gemini-1.5-pro-exp-0801":
        model = genai.GenerativeModel('gemma-2-27b-it', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    else:
        model = genai.GenerativeModel('gemini-1.5-flash', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    
    friendly_name = model_names[model.model_name] # Selects the correct friendly name
    await ctx.send(f"Switched to {friendly_name}") # Sends the current bot setting
    logging.info(f"Switched to {friendly_name}") # Logs the current bot setting
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}')) # Change the status to the current bot setting

@client.command(name="which")
async def which(ctx: commands.Context):
    """
    See which model you are using. 
    """
    global model
    friendly_name = model_names[model.model_name] # Selects the correct friendly name
    await ctx.send(f"You are using {friendly_name}") # Sends the current bot name
    

# Add commands
client.add_command(prompt(model))  # Adds the command prompt from the other file
client.add_command(sync) # Adds the command sync from the other file

# Run the bot
client.run(config['DiscordToken'])
