import discord
from discord.ext import commands

from bot.events import register_events
from bot.setup import get_initial_state, load_config, setup_gemini, setup_logging
from commands import register_commands
from packages.utilities.code_execution import start_docker_daemon


def main() -> None:
    """Run the bot."""
    config = load_config()
    setup_logging()

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
