from __future__ import annotations
from typing import TYPE_CHECKING
import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import GeminiBot

class UsageCog(commands.Cog, name="Usage"):
    """A cog for displaying bot usage statistics."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    @commands.hybrid_command(name="usage")
    async def usage_command(self, ctx: commands.Context) -> None:
        """Shows the total token count for the current session."""
        # Access the latest_token_count directly from the bot instance
        await ctx.send(f"Total Token Count: {self.bot.latest_token_count}", ephemeral=True)

async def setup(bot: "GeminiBot"):
    """Adds the UsageCog to the bot."""
    await bot.add_cog(UsageCog(bot))