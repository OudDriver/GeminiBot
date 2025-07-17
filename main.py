import logging
import os
import sys

import discord
from discord.ext import commands
from google.genai import Client

from bot.config import ConfigManager
# Use the refactored initialization function
from bot.setup import initialize_temp_config, setup_gemini, setup_logging
from packages.utilities.code_execution import start_docker_daemon
from packages.utilities.file_utils import validate_config_files, read_temp_config


class GeminiBot(commands.Bot):
    """A custom bot class to hold state and manage background tasks."""

    # Removed initial_state from __init__ signature
    def __init__(self, *, config: ConfigManager, genai_client: Client, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.genai_client = genai_client
        self.logger = logging.getLogger(self.__class__.__name__)
        self.latest_token_count: int = 0 # New: Bot-wide token count

    async def setup_hook(self) -> None:
        """
        This hook is called once when the bot logs in, before any events are dispatched.
        It's the perfect place to start background tasks and load all our cogs.
        """
        # Start the config hot-reloader
        self.loop.create_task(self.config.start_hot_reload_loop())
        self.logger.info("Configuration hot-reload task has been started.")

        # Automatically discover and load cogs from the 'commands' directory
        cogs_dir = "commands"
        self.logger.info("Loading extensions from './%s'...", cogs_dir)
        for filename in os.listdir(f"./{cogs_dir}"):
            if filename.endswith(".py") and not filename.startswith("_"):
                extension_name = f"{cogs_dir}.{filename[:-3]}"
                try:
                    await self.load_extension(extension_name)
                    self.logger.info("Successfully loaded extension: %s", filename)
                except commands.errors.NoEntryPointError:
                    self.logger.debug("Skipping %s as it is not a loadable cog.", filename)
                except Exception as e:
                    self.logger.error("Failed to load extension %s.", filename, exc_info=e)


def main() -> None:
    """Run the bot."""
    setup_logging()
    logger = logging.getLogger(__name__)

    if not validate_config_files():
        logger.fatal("Config files isn't complete. Please check again!")
        sys.exit(1)

    try:
        config = ConfigManager("config.json")
    except Exception:
        logger.fatal("Failed to load initial configuration. Bot cannot start.", exc_info=True)
        sys.exit(1)

    start_docker_daemon() # Make sure Docker is running for code execution tools

    initialize_temp_config(config.get_all_config()) # Pass the full config dict for defaults

    # Note: If GeminiAPIkey changes, a restart is needed to re-initialize the client.
    genai_client = setup_gemini(config.get("GeminiAPIkey"))

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True # Required for voice commands

    # Pass only config and genai_client to GeminiBot
    client = GeminiBot(config=config, genai_client=genai_client, command_prefix="!", intents=intents)

    # Note: If DiscordToken changes, the bot must be restarted.
    client.run(config.get("DiscordToken"), log_handler=None)

if __name__ == "__main__":
    main()