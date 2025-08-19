# packages/cogs/info.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from packages.utilities.file_utils import read_temp_config

if TYPE_CHECKING:
    from main import GeminiBot # Assuming GeminiBot is in your project root


logger = logging.getLogger(__name__)


class InfoCog(commands.Cog, name="Info"):
    """A cog for providing information about the bot's current configuration."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot # Store the bot instance to access bot.config

    @commands.hybrid_command(name="which")
    async def which(self, ctx: commands.Context) -> None:
        temp_config = read_temp_config() # Read the current temporary config

        current_model_id = temp_config.get("model", "default-model-not-set")
        model_names = self.bot.config.get("ModelNames", {})
        friendly_name = model_names.get(current_model_id, current_model_id) # Use ID as fallback

        sys_prompt_name = temp_config.get("system_prompt_name", "None")

        thinking = temp_config.get("thinking", False) # Default to False if not set
        budget = temp_config.get("thinking_budget", 0) # Default to 0 if not set

        active_tools_name = temp_config.get("active_tools_name", "None")


        # Construct the reply message
        reply_message = (
            f"Using model **{friendly_name}**.\n"
            f"System prompt: **{sys_prompt_name}**.\n"
            f"Active tools: **{active_tools_name}**.\n"
            f"Thinking is **{'enabled' if thinking or budget != 0 else 'disabled'}**.\n"
            f"Thinking budget is **{budget if budget > -1 else 'automatic'}**."
        )

        await ctx.reply(
            reply_message,
            ephemeral=True,
        )

async def setup(bot: "GeminiBot"):
    """Adds the InfoCog to the bot."""
    await bot.add_cog(InfoCog(bot))