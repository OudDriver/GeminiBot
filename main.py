import logging
import sys

import discord
from discord.ext import commands

from bot.events import register_events
from bot.setup import get_initial_state, setup_gemini, setup_logging
from commands import register_commands
from packages.utilities.code_execution import start_docker_daemon
from packages.utilities.file_utils import load_config, validate_config_files


def main() -> None:
    """Run the bot."""
    config = load_config()
    setup_logging()

    logger = logging.getLogger(__name__)

    if not validate_config_files():
        logger.fatal("Config files isn't complete. Please check again!")
        sys.exit(1)

    start_docker_daemon()
    genai_client = setup_gemini(config["GeminiAPIkey"])
    initial_state = get_initial_state(config)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    client = commands.Bot(command_prefix="!", intents=intents)

    register_events(client, initial_state, genai_client)
    register_commands(client, initial_state, config, genai_client)

    client.run(config["DiscordToken"], log_handler=None)

if __name__ == "__main__":
    main()
