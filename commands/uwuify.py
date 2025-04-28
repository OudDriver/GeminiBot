import logging

from discord.ext import commands

from packages.utilities.file_utils import save_temp_config


def setup_uwu_command(client: commands.Bot, initial_state: dict) -> None:
    """Setups the uwu command.

    Args:
        client: The discord bot client.
        initial_state: The initial state.
    """
    logger = logging.getLogger(__name__)
    @client.hybrid_command(name="uwuify")
    @commands.has_permissions(manage_messages=True)
    async def uwuify(ctx: commands.Context) -> None:
        """Why."""
        initial_state["current_uwu_status"] = not initial_state["current_uwu_status"]
        save_temp_config(
            initial_state["model"],
            initial_state["system_prompt_data"],
            initial_state["current_uwu_status"],
        )

        if initial_state["current_uwu_status"]:
            await ctx.reply(
                "Enabled Uwuifier. Beware that asking it for code will not work.",
            )
            logger.info("Enabled Uwuifier.")
        else:
            await ctx.reply("Disabled Uwuifier.")
            logger.info("Disabled Uwuifier.")
