from __future__ import annotations # For postponed evaluation of type annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

# Import the read_temp_config utility
from packages.utilities.file_utils import read_temp_config

if TYPE_CHECKING:
    from discord.message import Message
    from main import GeminiBot # Assuming GeminiBot is in your project root or accessible via module path


logger = logging.getLogger(__name__)


class EventsCog(commands.Cog, name="Events"):
    """A cog for handling general Discord bot events."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event listener that triggers when the bot is ready."""
        temp_config = read_temp_config()
        current_model_id = temp_config.get("model")
        model_names = self.bot.config.get("ModelNames", {})
        friendly_name = model_names.get(current_model_id, current_model_id)

        logger.info(f"Logged in as {self.bot.user}. Using {friendly_name}")

        await self.bot.change_presence(
            activity=discord.CustomActivity(
                name=f"Hello there! I am using {friendly_name}",
            ),
        )

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Event listener that triggers on every message."""
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return

        ctx = await self.bot.get_context(message)

        # This condition already ensures it only triggers on mention or reply
        if self.bot.user in message.mentions or message.reference is not None:
            prompt_cog = self.bot.get_cog("Prompt")
            if prompt_cog:
                try:
                    # Call the renamed method
                    await prompt_cog.handle_ai_interaction(ctx)
                except Exception as e:
                    logger.exception("Error in on_message event (manual prompt invocation):")
                    await ctx.send(
                        f"An error occurred while processing your request: `{e}`",
                        ephemeral=True
                    )
            else:
                logger.warning("PromptCog not found. Cannot respond to mention/reply.")
                await ctx.send(
                    "Error: My AI processing module is not loaded. Please contact an administrator.",
                    ephemeral=True
                )

        # It's important to keep this for other commands (if you have any besides /prompt)
        await self.bot.process_commands(message)

async def setup(bot: "GeminiBot"):
    """Adds the EventsCog to the bot."""
    await bot.add_cog(EventsCog(bot))