from discord.ext import commands

@commands.hybrid_command()
async def get_latest_thought(ctx: commands.Context):
    from commands.prompt import thought
    
    if not thought:
        return
    
    await ctx.send(thought)
