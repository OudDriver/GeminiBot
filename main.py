
import discord
from discord.ext import commands
import os

from bot.setup import load_config, setup_logging, setup_gemini, get_initial_state
from bot.events import register_events

from commands import register_commands
from commands.sync import sync
from commands.thought import thought
from commands.secret import secret
from commands.voice import voice, leave
from commands.usage import usage

def main():
    """Main function to run the bot."""
    temp_config_path = "temp/temp_config.json"
    try:
        os.remove(temp_config_path)
        print("Removed temp_config.json")  
    except FileNotFoundError:
        print("temp_config.json not found, no need to remove.")
    except OSError as e:
        print(f"Error removing temp_config.json: {e}")

    config = load_config()
    setup_logging()
    genai_client = setup_gemini(config['GeminiAPIkey'])
    initial_state = get_initial_state(config)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    client = commands.Bot(command_prefix='!', intents=intents)

    register_events(client, initial_state, genai_client)
    register_commands(client, initial_state, config)
    
    client.add_command(sync)
    client.add_command(thought)
    client.add_command(secret)
    client.add_command(voice(genai_client))  
    client.add_command(leave)
    client.add_command(usage)

    client.run(config['DiscordToken'])

if __name__ == "__main__":
    main()