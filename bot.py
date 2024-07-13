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
SYSTEM_PROMPT = "You are a friendly, fun, and knowledgeable multimodal AI assistant. If a user asks about topics you don't know the answer to, politely inform them that you cannot answer on those subjects. If a user becomes hostile or uses inappropriate language, maintain a calm and professional demeanor. When generating stories or poems, feel free to use figurative language, such as metaphors, similes, and personification, to make your writing more vivid and engaging. Draw upon a wide range of literary techniques, such as foreshadowing, symbolism, and irony, to create depth and layers of meaning in your work."

TOOLS = 'code_execution'

genai.configure(api_key=config['GeminiAPI'])
model = genai.GenerativeModel('gemini-1.5-flash', tools=TOOLS, system_instruction=SYSTEM_PROMPT)

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# Map internal model names to user-friendly names
model_names = {
    'models/gemini-1.5-flash': 'Gemini 1.5 Flash',
    'models/gemini-1.5-pro': 'Gemini 1.5 Pro',
    'models/gemma-2-27b-it': 'Gemma 2 27b it'
}

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("bot.log"),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}. Using {model.model_name}')
    friendly_name = model_names[model.model_name]
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))

@client.command(name="toggle")
async def toggle(ctx: commands.Context):
    """
    Toggles between Gemini 1.5 Pro and Gemini 1.5 Flash. 
    """
    global model
    if model.model_name == "models/gemini-1.5-flash":
        model = genai.GenerativeModel('gemini-1.5-pro', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    elif model.model_name == "models/gemini-1.5-pro":
        model = genai.GenerativeModel('gemma-2-27b-it', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    else:
        model = genai.GenerativeModel('gemini-1.5-flash', tools=TOOLS, system_instruction=SYSTEM_PROMPT)
    
    friendly_name = model_names[model.model_name]
    await ctx.send(f"Switched to {friendly_name}")
    logging.info(f"Switched to {friendly_name}")
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))
    
@client.command(name="which")
async def which(ctx: commands.Context):
    """
    See which model you are using. 
    """
    global model
    friendly_name = model_names[model.model_name]
    await ctx.send(f"You are using {friendly_name}")
    

# Add commands
client.add_command(prompt(model))  # Pass the model here
client.add_command(sync)

# Run the bot
client.run(config['DiscordToken'])
