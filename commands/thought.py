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

@commands.hybrid_command()
@commands.has_permissions(administrator=True)
async def secret(ctx: commands.Context):
    """
    Shows the bot's kept secret

    Args:
        ctx: The context of the command invocation
    """
    from commands.prompt import secrets
    
    if not secrets:
        await ctx.send("None", ephemeral=True)
        return
    
    await ctx.send(secrets, ephemeral=True)