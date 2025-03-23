from discord.ext import commands

@commands.hybrid_command()
async def thought(ctx: commands.Context):
    """
    Shows what the bot is thinking

    Args:
        ctx: The context of the command invocation
    """
    from commands.prompt import thought

    if not thought:
        await ctx.send("None")
        return

    await ctx.send(thought)

