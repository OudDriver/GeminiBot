from discord.ext import commands


@commands.hybrid_command()
async def usage(ctx: commands.Context) -> None:
    """Syncs slash commands.

    Args:
        ctx: The context of the command invocation

    """
    from commands.prompt import latest_token_count
    await ctx.send(f"Total Token Count: {latest_token_count}", ephemeral=True)


