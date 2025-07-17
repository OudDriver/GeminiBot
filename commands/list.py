import discord
from discord.ext import commands


class ListCog(commands.Cog, name="Listing"):
    """A cog for listing various configured items."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    @discord.app_commands.command(name="list", description="Lists available models, system prompts, and tools.")
    async def list_all(self, interaction: discord.Interaction):
        """Handles the /list command to show all available resources."""
        # Access the LIVE config directly from the bot instance
        prompts = self.bot.config.get("SystemPrompts", [])
        tools = self.bot.config.get("Tools", {})
        models = self.bot.config.get("ModelNames", {})

        embed = discord.Embed(
            title="Available Bot Resources",
            description="Live data from `config.json`. Changes will appear here automatically.",
            color=discord.Color.blue()
        )

        # Format and add system prompts to the embed
        prompt_names = [p.get("Name", "Unnamed Prompt") for p in prompts]
        if prompt_names:
            embed.add_field(name="System Prompts", value="\n".join(f"• {name}" for name in prompt_names), inline=False)

        # Format and add models to the embed
        if models:
            model_list = [f"• **{name}** (ID: `{key}`)" for key, name in models.items()]
            embed.add_field(name="AI Models", value="\n".join(model_list), inline=False)

        # Format and add tools to the embed
        if tools:
            embed.add_field(name="Tools", value="\n".join(f"• {name}" for name in tools.keys()), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: "GeminiBot"):
    """Adds the ListCog to the bot."""
    await bot.add_cog(ListCog(bot))