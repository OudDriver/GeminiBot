import logging

import discord
from discord.ext.commands import Bot
from discord.message import Message
from google.genai import Client

from commands.prompt import prompt

logger = logging.getLogger(__name__)

def register_events(
        client: Bot,
        initial_state: dict[str, any],
        genai_client: Client,
) -> None:
    """Register event handlers with the Discord client."""

    @client.event
    async def on_ready() -> None:
        model = initial_state["model_options"][initial_state["current_model_index"]]

        logger.info(f"Logged in as {client.user}. Using {model}")

        current_model_index = initial_state["current_model_index"]
        model_option = initial_state["model_options"][current_model_index]
        friendly_name = initial_state["model_clean_names"][model_option]

        await client.change_presence(
            activity=discord.CustomActivity(
                name=f"Hello there! I am using {friendly_name}",
            ),
        )

    @client.event
    async def on_message(message: Message) -> None:
        if message.author == client.user:
            return

        prompt_command = prompt(
            tools=initial_state["active_tools"],
            genai_client=genai_client,
        )

        if client.user in message.mentions or message.reference is not None:
            ctx = await client.get_context(message)
            try:
                await prompt_command(ctx)
            except Exception as e:
                logger.exception("Error in on_message event:")
                await ctx.send(
                    f"An error occurred while processing your request: `{e}`",
                )

        await client.process_commands(message)
