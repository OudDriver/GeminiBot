from discord.ext import commands

def setup_which_command(client, initial_state, config):
    @client.hybrid_command(name="which")
    async def which(ctx: commands.Context):
        """Shows which model is currently active."""
        friendly_name = config["ModelNames"][initial_state["model"]]
        await ctx.reply(f"You are using {friendly_name}", ephemeral=True)