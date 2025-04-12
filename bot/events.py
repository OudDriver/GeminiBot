
import logging
import discord
from commands.prompt import prompt

def register_events(client, initial_state, genai_client):
    """Registers event handlers with the Discord client."""

    @client.event
    async def on_ready():
        logging.info(f'Logged in as {client.user}. Using {initial_state["model_options"][initial_state["current_model_index"]]}')
        friendly_name = initial_state["model_clean_names"][initial_state["model_options"][initial_state["current_model_index"]]]
        await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        prompt_command = prompt(tools=initial_state["active_tools"], genai_client=genai_client)

        if client.user in message.mentions or message.reference is not None:
            ctx = await client.get_context(message)
            try:
                await prompt_command(ctx)
            except Exception as e:
                logging.exception("Error in on_message event:")
                await ctx.send(f"An error occurred while processing your request: `{e}`")

        await client.process_commands(message)