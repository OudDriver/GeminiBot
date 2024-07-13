from discord.ext import commands
import json

with open('config.json') as f:
    config = json.loads(f.read())

@commands.hybrid_command()
async def sync(ctx: commands.Context):
    """Syncs slash commands."""
    if ctx.author.id == int(config.get('owner_id', 0)):
        await ctx.send(f'Syncing...')
        synced = await ctx.bot.tree.sync()
        await ctx.send(f'Synced {len(synced)} Command(s): {synced}')
    else:
        await ctx.send('You must be the owner to use this command!')

