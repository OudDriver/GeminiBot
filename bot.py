from discord.ext import commands
from discord import app_commands
from google import genai
from google.genai.types import GoogleSearch, ToolCodeExecution, Tool
import discord
import json
import logging
import os

from commands.prompt import prompt
from commands.sync import sync
from commands.thought import thought, secret
from commands.voice import voice, leave
from commands.usage import usage

from packages.internet import search_duckduckgo, make_get_request, get_wikipedia_page
from packages.weather import get_weather
from packages.wolfram import wolfram_alpha
from packages.utils import timeout, hi, execute_code
from packages.memory_save import save_memory

# Load configuration from config.json
CONFIG = json.load(open("config.json"))

# Define system prompts and available tools for the bot
SYSTEM_PROMPTS = CONFIG["SystemPrompts"]
TOOLS = {
    "Default": [get_weather, make_get_request, get_wikipedia_page, wolfram_alpha, hi, timeout, execute_code, search_duckduckgo, save_memory],
    "Google Search": [Tool(google_search=GoogleSearch())],
    "Code Execution": [Tool(code_execution=ToolCodeExecution())]
}

# Configure Google Gemini API key
genai_client = genai.Client(api_key=CONFIG['GeminiAPIkey'], http_options={'api_version': 'v1alpha'})

# Initialize system prompt
current_sys_prompt_index = 0
system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
system_prompt_data = system_prompt['SystemPrompt']

# Get available model options
model_options = [key for key in CONFIG["ModelNames"]]

# Set initial active tools
active_tools_index = 0
tool_names = list(TOOLS.keys())
active_tools = TOOLS[tool_names[active_tools_index]]

# Set current uwu status for tracking
current_uwu_status = False

# Set initial model and save temporary configuration
current_model_index = 0
model = model_options[current_model_index]

if not os.path.isdir("./temp"):
    os.makedirs("./temp")

with open("temp/temp_config.json", "w") as TEMP_CONFIG:
    json.dump({"model": model, "system_prompt": system_prompt_data, "uwu": current_uwu_status}, TEMP_CONFIG)

# Set up Discord bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)

# Configure logging to file and console
logging.basicConfig(level=logging.INFO,  # Set default logging level
                    format='%(asctime)s - %(levelname)s - %(message)s',  # Time - Level Name - message
                    handlers=[  # Add handlers
                        logging.FileHandler("bot.log", encoding='utf-8'),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])


# Event handler for when the bot is ready
@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}. Using {model_options[current_model_index]}')
    friendly_name = CONFIG["ModelNames"][model_options[current_model_index]]
    await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))

@client.hybrid_command(name="uwuify")
@commands.has_permissions(manage_messages=True)
async def uwuify(ctx: commands.Context):
    """
    Why!?!?

    Args:
        ctx: The context of the command invocation
    """
    global current_uwu_status
    with open("temp/temp_config.json", "r") as TEMP_CFG:
        data = json.load(TEMP_CFG)

    # Get current model
    selected_model = model_options[current_model_index]

    # Get current system prompt
    current_system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
    current_system_prompt_data = current_system_prompt['SystemPrompt']

    if not data["uwu"]:
        current_uwu_status = True
        with open("temp/temp_config.json", "w") as TEMP_CFG:
            json.dump({"model": selected_model, "system_prompt": current_system_prompt_data, "uwu": current_uwu_status}, TEMP_CFG)
        await ctx.reply("Enabled Uwuifier. Beware that asking it for code will not work.")
        logging.info("Enabled Uwuifier.")
    else:
        current_uwu_status = False
        with open("temp/temp_config.json", "w") as TEMP_CFG:
            json.dump({"model": selected_model, "system_prompt": current_system_prompt_data, "uwu": current_uwu_status}, TEMP_CFG)
        await ctx.reply("Disabled Uwuifier.")
        logging.info("Disabled Uwuifier.")


@client.hybrid_command(name="toggle")
@app_commands.choices(toggles=[
    app_commands.Choice(name="System Prompt", value="sys"),
    app_commands.Choice(name="Model", value="model"),
    app_commands.Choice(name="Tools", value="tools")
])
async def toggle(ctx: commands.Context, toggles: str):
    """
    Toggles something for the bot

    Args:
        ctx: The context of the command invocation
        toggles: What to toggle
    """
    global model, current_sys_prompt_index, current_model_index, active_tools_index, active_tools

    if toggles == 'sys':
        # Cycle through available models
        current_model_index = (current_model_index + 1) % len(model_options)
        selected_model = model_options[current_model_index]

        # Cycle through available system prompts
        current_sys_prompt_index = (current_sys_prompt_index + 1) % len(SYSTEM_PROMPTS)
        changed_system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
        changed_system_prompt_data = changed_system_prompt['SystemPrompt']
        system_prompt_name = changed_system_prompt['Name']

        # Save updated configuration to temporary file
        with open("temp/temp_config.json", "w") as SYS_TEMP_CONFIG:
            json.dump({"model": selected_model, "system_prompt": changed_system_prompt_data, "uwu": current_uwu_status}, SYS_TEMP_CONFIG)

        logging.info(f"Switched to {system_prompt_name}")

        await ctx.send(f"Using {system_prompt_name}.")
    elif toggles == "model":
        # Cycle through available models
        current_model_index = (current_model_index + 1) % len(model_options)
        selected_model = model_options[current_model_index]

        # Get current system prompt
        current_system_prompt = SYSTEM_PROMPTS[current_sys_prompt_index]
        current_system_prompt_data = current_system_prompt['SystemPrompt']

        # Save updated configuration to temporary file
        with open("temp/temp_config.json", "w") as SYS_TEMP_CONFIG:
            json.dump({"model": selected_model, "system_prompt": current_system_prompt_data, "uwu": current_uwu_status}, SYS_TEMP_CONFIG)

        friendly_name = CONFIG["ModelNames"][selected_model]
        logging.info(f"Switched to {friendly_name}")

        await ctx.send(f"Switched to {friendly_name}")

        await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))
    elif toggles == 'tools':
        # Cycle through available toolsets
        tools_names = list(TOOLS.keys())
        active_tools_index = (active_tools_index + 1) % len(tools_names)
        active_tool_name = tools_names[active_tools_index]
        active_tools = TOOLS[active_tool_name]

        logging.info(f"Switched to toolset {active_tool_name}")

        await ctx.send(f"Switched to toolset: {active_tool_name}")

        # Update the prompt command to use the new active tools
        client.remove_command('prompt')
        client.add_command(prompt(active_tools, genai_client))


# Command to show the currently used model
@client.hybrid_command(name="which")
async def which(ctx: commands.Context):
    """
    Shows which model is currently active.

    Args:
        ctx: The context of the command invocation
    """
    friendly_name = CONFIG["ModelNames"][model_options[current_model_index]]
    await ctx.reply(f"You are using {friendly_name}", ephemeral=True)

# Add available commands to the bot
client.add_command(prompt(active_tools, genai_client))
client.add_command(sync)
client.add_command(thought)
client.add_command(secret)
client.add_command(voice(genai_client))
client.add_command(leave)
client.add_command(usage)

# Run the bot with the token from the configuration
client.run(CONFIG['DiscordToken'])
