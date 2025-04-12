from discord.ext import commands

def setup_list_command(client, initial_state):
    @client.hybrid_command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def list_sys(ctx: commands.Context):
        """Lists all system prompts"""
        all_sys_dict = initial_state['system_prompts']
        all_tools_dict = initial_state['tools']

        all_sys = []
        all_models = list(initial_state["model_clean_names"].values()) # It's an array!
        all_tools = list(all_tools_dict)

        for i in all_sys_dict:
            all_sys.append(i['Name'])

        formatted_string_sys = ''
        for i, v in enumerate(all_sys):
            formatted_string_sys += f"\n{i + 1}: {v}"

        formatted_string_models = ""
        for i, v in enumerate(all_models):
            formatted_string_models += f"\n{i + 1}: {v}"

        formatted_string_tools = ""
        for i, v in enumerate(all_tools):
            formatted_string_tools += f"\n{i + 1}: {v}"

        await ctx.reply(f"The system prompts include: {formatted_string_sys}\n\nThe models include: {formatted_string_models}\n\nThe tools include: {formatted_string_tools}", ephemeral=True)