from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from packages.utilities.file_utils import read_temp_config

if TYPE_CHECKING:
    from main import GeminiBot


class ThoughtCog(commands.Cog, name="Thought"):
    """A cog for displaying the bot's internal thought process."""

    def __init__(self, bot: GeminiBot) -> None:
        """Initialize the Cog."""
        self.bot = bot

    @commands.hybrid_command(name="thought")
    async def thought_command(self, ctx: commands.Context) -> None:
        """Show the bot's thought process."""
        temp_config = read_temp_config()

        thoughts = temp_config.get("thought", []) # Default to empty list if not found
        thoughts_found = ""

        if not thoughts:
            await ctx.send("None", ephemeral=True)
            return

        await ctx.send(thoughts_found, ephemeral=True)

async def setup(bot: GeminiBot) -> None:
    """Adds the ThoughtCog to the bot."""
    await bot.add_cog(ThoughtCog(bot))
