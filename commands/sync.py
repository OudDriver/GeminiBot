from discord.ext import commands
from discord.app_commands.models import AppCommand
import json

with open('config.json') as f:
    config = json.loads(f.read())

@commands.hybrid_command()
async def sync(ctx: commands.Context):
    """
    Syncs slash commands.

    Args:
        ctx: The context of the command invocation
    """
    if str(ctx.author.id) == str(config['OwnerID']):
        await ctx.reply(f'Syncing...', ephemeral=True)
        # noinspection PyUnresolvedReferences
        synced = await ctx.bot.tree.sync()
        synced_commands = ""
        for command in synced:
            synced_commands += command.name + ', '
        await ctx.reply(f'Synced {len(synced)} Command(s): {synced_commands}', ephemeral=True)
    else:
        await ctx.reply('You must be the owner to use this command!', ephemeral=True)

