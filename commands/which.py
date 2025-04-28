from discord.ext import commands


def setup_which_command(
        client: commands.Bot,
        initial_state: dict,
        config: dict,
) -> None:
    """Setups the which command.

    Args:
        client: The discord bot client.
        initial_state: The initial state.
        config: The config file in dict.
    """
    @client.hybrid_command(name="which")
    async def which(ctx: commands.Context) -> None:
        """Shows which model is currently active."""
        friendly_name = config["ModelNames"][initial_state["model"]]
        current_sys_prompt_index = initial_state["current_sys_prompt_index"]
        sys_prompts = config["SystemPrompts"]

        sys_prompt_name  = sys_prompts[current_sys_prompt_index]["Name"]
        await ctx.reply(
            (
                f"You are using {friendly_name} "
                f"with the system prompt named {sys_prompt_name}."
            ),
            ephemeral=True,
        )
