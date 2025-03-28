from discord.ext import commands

def setup_which_command(client, initial_state, config):
    @client.hybrid_command(name="which")
    async def which(ctx: commands.Context):
        """Shows which model is currently active."""
        friendly_name = config["ModelNames"][initial_state["model"]]
        current_sys_prompt_index = initial_state['current_sys_prompt_index']
        sys_prompts = config["SystemPrompts"]

        sys_prompt_name  = sys_prompts[current_sys_prompt_index]["Name"]
        await ctx.reply(f"You are using {friendly_name} with the system prompt named {sys_prompt_name}.", ephemeral=True)