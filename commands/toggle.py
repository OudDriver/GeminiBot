from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands

from packages.utilities.file_utils import save_temp_config

if TYPE_CHECKING:
    from discord.ext import commands
    from discord.ext.commands import Bot

logger = logging.getLogger(__name__)

async def _handle_toggle_sys_prompt(
    ctx: commands.Context, initial_state: dict[str, Any], index: int | None,
) -> None:
    """Handles toggling the system prompt."""
    system_prompts = initial_state.get("system_prompts", [])
    if not system_prompts:
        await ctx.reply("No system prompts available to switch to.", ephemeral=True)
        return

    max_index = len(system_prompts)
    if index and not (1 <= index <= max_index):
        await ctx.reply(
            (
                f"Index out of bounds! Please use a number between 1 and {max_index}. "
                f"Use the !list command for more information."
            ),
            ephemeral=True,
        )
        return

    if index is None:
        current_index = initial_state.get("current_sys_prompt_index", -1)
        new_index = (current_index + 1) % max_index
    else:
        new_index = index - 1

    initial_state["current_sys_prompt_index"] = new_index
    selected_prompt = system_prompts[new_index]
    system_prompt_name = selected_prompt.get("Name", f"Prompt {new_index + 1}")
    system_prompt_data = selected_prompt.get("SystemPrompt", "")
    initial_state["system_prompt_data"] = system_prompt_data

    save_temp_config(system_prompt_data=system_prompt_data)
    logger.info(f"Switched to system prompt: {system_prompt_name}")
    await ctx.send(f"Using system prompt: {system_prompt_name}.")


async def _handle_toggle_model(
    ctx: commands.Context,
    client: Bot, initial_state: dict[str, Any],
    index: int | None,
) -> None:
    """Handles toggling the model."""
    model_options = initial_state.get("model_options", [])
    if not model_options:
        await ctx.reply("No models available to switch to.", ephemeral=True)
        return

    max_index = len(model_options)
    if index and not (1 <= index <= max_index):
        await ctx.reply(
            (
                f"Index out of bounds! Please use a number between 1 and {max_index}. "
                f"Use the !list command for more information."
            ),
            ephemeral=True,
        )
        return

    if index is None:
        current_index = initial_state.get("current_model_index", -1)
        new_index = (current_index + 1) % max_index
    else:
        new_index = index - 1

    initial_state["current_model_index"] = new_index
    selected_model_option = model_options[new_index]
    initial_state["model"] = selected_model_option

    save_temp_config(model=selected_model_option)

    model_clean_names = initial_state.get("model_clean_names", {})
    friendly_name = model_clean_names.get(selected_model_option, selected_model_option)

    logger.info(f"Switched to model: {friendly_name}")
    await ctx.send(f"Switched to model: {friendly_name}.")
    try:
        await client.change_presence(
            activity=discord.CustomActivity(
                name=f"Hello there! I am using {friendly_name}",
            ),
        )
    except Exception:
        logger.exception("Failed to update presence.")


async def _handle_toggle_tools(
    ctx: commands.Context,
    initial_state: dict[str, Any],
    index: int | None,
) -> None:
    """Handles toggling the active toolset."""
    tools = initial_state.get("tools", {})
    tools_names = list(tools.keys())

    if not tools_names:
        await ctx.reply("No toolsets available to switch to.", ephemeral=True)
        return

    max_index = len(tools_names)
    if index and not (1 <= index <= max_index):
        await ctx.reply(
            (
                f"Index out of bounds! Please use a number between 1 and {max_index}. "
                f"Use the !list command for more information."
            ),
            ephemeral=True,
        )
        return

    if index is None:
        current_index = initial_state.get("active_tools_index", -1)
        new_index = (current_index + 1) % max_index
    else:
        new_index = index - 1

    initial_state["active_tools_index"] = new_index
    tool_name = tools_names[new_index]
    initial_state["active_tools"] = tools.get(tool_name, [])

    logger.info(f"Switched to toolset: {tool_name}")
    await ctx.send(f"Switched to toolset: {tool_name}.")


# --- Main Command Setup ---

def setup_toggle_command(client: Bot, initial_state: dict[str, Any]) -> None:
    """Set up the toggle command."""
    @client.hybrid_command(name="toggle")
    @app_commands.choices(toggles=[
        app_commands.Choice(name="System Prompt", value="sys"),
        app_commands.Choice(name="Model", value="model"),
        app_commands.Choice(name="Tools", value="tools"),
    ])
    async def toggle(
            ctx: commands.Context,
            toggles: str,
            index: int | None = None,
    ) -> None:
        """Toggle system prompt, model, or tools for the bot."""
        toggle_handlers = {
            "sys": lambda: _handle_toggle_sys_prompt(ctx, initial_state, index),
            "model": lambda: _handle_toggle_model(ctx, client, initial_state, index),
            "tools": lambda: _handle_toggle_tools(ctx, initial_state, index),
        }

        handler = toggle_handlers.get(toggles)
        if handler:
            await handler()
        else:
            logger.warning(f"Invalid toggle value received: {toggles}")
            await ctx.reply("Invalid toggle option specified.", ephemeral=True)
