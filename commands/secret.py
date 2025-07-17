from __future__ import annotations
from typing import TYPE_CHECKING
import discord
from discord.ext import commands

from packages.utilities.file_utils import read_temp_config

if TYPE_CHECKING:
    from main import GeminiBot

class SecretCog(commands.Cog, name="Secret"):
    """A cog for displaying the bot's configured secret (developer/admin only)."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    @commands.hybrid_command(name="secret")
    @commands.has_permissions(administrator=True) # Check permissions at the command level
    async def secret_command(self, ctx: commands.Context) -> None:
        temp_config = read_temp_config()

        secrets = temp_config.get("secret", "None") # Default to "None" if key not found

        await ctx.send(secrets, ephemeral=True) # Always ephemeral for secrets

async def setup(bot: "GeminiBot"):
    """Adds the SecretCog to the bot."""
    await bot.add_cog(SecretCog(bot))