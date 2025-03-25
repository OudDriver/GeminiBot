from discord.ext import commands

def setup_list_command(client, initial_state):
    @client.hybrid_command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def list_sys(ctx: commands.Context):
        """Lists all system prompts"""
        all_sys_dict = initial_state['system_prompts']
        all_sys = []
        for i in all_sys_dict:
            all_sys.append(i['Name'])

        formatted_list = ""
        if len(all_sys) > 1:
            formatted_list = ', '.join(all_sys[:-1]) + ', and ' + all_sys[-1]
        else:
            formatted_list = all_sys[0] if all_sys else "none"

        await ctx.reply(f"The system prompts include: {formatted_list}.", ephemeral=True)