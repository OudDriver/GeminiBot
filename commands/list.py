from typing import Any

from discord.ext import commands


def setup_list_command(client: commands.Bot, initial_state: dict[str, Any]) -> None:
    """Set up the list command."""
    @client.hybrid_command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def list_sys(ctx: commands.Context) -> None:
        """List all system prompts."""
        all_sys_dict = initial_state["system_prompts"]
        all_tools_dict = initial_state["tools"]

        all_models = list(initial_state["model_clean_names"].values()) # It's an array!
        all_tools = list(all_tools_dict)

        all_sys = [sys["Name"] for sys in all_sys_dict]

        formatted_string_sys = ""
        for i, v in enumerate(all_sys):
            formatted_string_sys += f"\n{i + 1}: {v}"

        formatted_string_models = ""
        for i, v in enumerate(all_models):
            formatted_string_models += f"\n{i + 1}: {v}"

        formatted_string_tools = ""
        for i, v in enumerate(all_tools):
            formatted_string_tools += f"\n{i + 1}: {v}"

        reply_message = (
            f"The system prompts include: {formatted_string_sys}\n\n"
            f"The models include: {formatted_string_models}\n\n"
            f"The tools include: {formatted_string_tools}"
        )

        await ctx.reply(content=reply_message, ephemeral=True)
