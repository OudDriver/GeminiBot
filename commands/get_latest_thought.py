from discord.ext import commands

@commands.hybrid_command()
async def get_thought(ctx: commands.Context):
    from commands.prompt import thought
    
    if not thought:
        await ctx.send("None")
        return
    
    await ctx.send(thought)
