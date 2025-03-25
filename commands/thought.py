from discord.ext import commands
from packages.utils import read_temp_config, remove_thought_tags

@commands.hybrid_command()
async def thought(ctx: commands.Context):
    """
    Shows what the bot is thinking

    Args:
        ctx: The context of the command invocation
    """
    temp_config = read_temp_config()

    thoughts = temp_config['thought']
    thoughts_found = ""

    for t in thoughts:
        thoughts_found += remove_thought_tags(t) + "\n\n"

    if not thoughts:
        await ctx.send("None")
        return

    await ctx.send(thoughts_found)

