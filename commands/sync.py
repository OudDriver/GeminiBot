from discord.ext import commands

from bot.setup import load_config

config = load_config()

@commands.hybrid_command()
async def sync(ctx: commands.Context) -> None:
    """Sync slash commands.

    Args:
        ctx: The context of the command invocation

    """
    if str(ctx.author.id) == str(config["OwnerID"]):
        await ctx.reply("Syncing...", ephemeral=True)
        synced = await ctx.bot.tree.sync()
        synced_commands = ""
        for command in synced:
            synced_commands += command.name + ", "
        await ctx.reply(
            f"Synced {len(synced)} Command(s): {synced_commands}",
            ephemeral=True,
        )
    else:
        await ctx.reply("You must be the owner to use this command!", ephemeral=True)

