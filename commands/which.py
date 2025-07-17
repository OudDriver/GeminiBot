from discord.ext import commands

from packages.utilities.file_utils import read_temp_config


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
        temp_config = read_temp_config()

        thinking = temp_config.get("thinking", None)
        budget = temp_config.get("thinking_budget", None)

        sys_prompt_name  = sys_prompts[current_sys_prompt_index]["Name"]
        await ctx.reply(
            (
                f"Using model {friendly_name} "
                f"with the system prompt named {sys_prompt_name}. "
                f"Thinking is {"enabled" if thinking or budget != 0 else "disabled"}. "
                f"Thinking budget is {budget if budget > -1 else "automatic"}."
            ),
            ephemeral=True,
        )
