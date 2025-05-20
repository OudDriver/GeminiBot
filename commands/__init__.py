from discord.ext.commands import Bot
from google.genai import Client

from commands.imagen import imagen
from commands.list import setup_list_command
from commands.secret import secret
from commands.sync import sync
from commands.thought import thought
from commands.toggle import setup_toggle_command
from commands.usage import usage
from commands.voice import leave, voice
from commands.which import setup_which_command


def register_commands(
        client: Bot,
        initial_state: dict[str, any],
        config: dict[str, str],
        genai_client: Client,
) -> None:
    """Register some command.

    Those include uwu, toggle, which, and list.
    """
    setup_toggle_command(client, initial_state)
    setup_which_command(client, initial_state, config)
    setup_list_command(client, initial_state)

    client.add_command(sync)
    client.add_command(thought)
    client.add_command(secret)
    client.add_command(voice(genai_client))
    client.add_command(leave)
    client.add_command(usage)
    client.add_command(imagen(genai_client))
