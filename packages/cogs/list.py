from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.setup import DEFAULT_TOOLS_MAP

if TYPE_CHECKING:
    from main import GeminiBot


class ListCog(commands.Cog, name="Listing"):
    """A cog for listing various configured items."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    @commands.hybrid_command(name="list", description="Lists available models, system prompts, and tools.")
    async def list_all(self, ctx: commands.Context):
        """Handles the /list command to show all available resources."""
        # Access the LIVE config directly from the bot instance
        prompts = self.bot.config.get("SystemPrompts", [])
        models = self.bot.config.get("ModelNames", {})

        embed = discord.Embed(
            title="Available Bot Resources",
            color=discord.Color.blue()
        )

        # Format and add system prompts to the embed
        prompt_names = [p.get("Name", "Unnamed Prompt") for p in prompts]
        if prompt_names:
            embed.add_field(
                name="System Prompts",
                value="\n".join(
                    f"{i + 1}. {name}" for i, name in enumerate(prompt_names)
                ),
                inline=False,
            )

        # Format and add models to the embed
        if models:
            model_list = []
            for i, (key, name) in enumerate(models.items()):
                model_list.append(f"{i + 1}. **{name}** (ID: `{key}`)")
            embed.add_field(name="AI Models", value="\n".join(model_list), inline=False)

        # Format and add tools to the embed
        if DEFAULT_TOOLS_MAP:
            embed.add_field(name="Tools", value="\n".join(f"{i + 1}. {name}" for i, name in enumerate(DEFAULT_TOOLS_MAP.keys())), inline=False)

        await ctx.reply(embed=embed, ephemeral=True)

async def setup(bot: "GeminiBot"):
    """Adds the ListCog to the bot."""
    await bot.add_cog(ListCog(bot))