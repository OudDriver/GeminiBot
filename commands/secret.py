from discord.ext import commands

from packages.utilities.file_utils import read_temp_config


@commands.hybrid_command()
@commands.has_permissions(administrator=True)
async def secret(ctx: commands.Context) -> None:
    """Show the bot's kept secret.

    Args:
        ctx: The context of the command invocation

    """
    temp_config = read_temp_config()

    secrets = temp_config["secret"]

    if not secrets:
        await ctx.send("None", ephemeral=True)
        return

    await ctx.send(secrets, ephemeral=True)
