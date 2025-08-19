from __future__ import annotations
from typing import TYPE_CHECKING
import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import GeminiBot

class SyncCog(commands.Cog, name="Sync"):
    """A cog for syncing Discord slash commands."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    @commands.hybrid_command(name="sync")
    async def sync_command(self, ctx: commands.Context) -> None:
        """Sync slash commands."""
        # Check against bot.owner_id first, which is set by discord.py if DiscordToken is valid
        # Fallback to config if bot.owner_id is not set (e.g., if token is bad or Discord API issues)
        is_owner = False
        if self.bot.owner_id: # This is the most reliable way after bot startup
            is_owner = ctx.author.id == self.bot.owner_id
        else:
            # Fallback if bot.owner_id isn't available for some reason, directly check bot's config
            owner_id_from_config = str(self.bot.config.get("OwnerID")) # Read OwnerID from bot's config
            is_owner = str(ctx.author.id) == owner_id_from_config

        if is_owner:
            await ctx.reply("Syncing...", ephemeral=True)
            synced = await ctx.bot.tree.sync()
            synced_commands = ", ".join([command.name for command in synced])
            await ctx.reply(
                f"Synced {len(synced)} Command(s): {synced_commands}",
                ephemeral=True,
            )
        else:
            await ctx.reply("You must be the owner to use this command!", ephemeral=True)

async def setup(bot: "GeminiBot"):
    """Adds the SyncCog to the bot."""
    await bot.add_cog(SyncCog(bot))