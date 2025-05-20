from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from packages.utilities.file_utils import read_temp_config, save_temp_config

if TYPE_CHECKING:
    from discord.ext.commands import Bot

logger = logging.getLogger(__name__)

async def _handle_toggle_sys_prompt(
    ctx: commands.Context,
    initial_state: dict[str, Any],
    index: int | None,
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
    client: Bot,
    initial_state: dict[str, Any],
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


async def _handle_toggle_thinking(
    ctx: commands.Context,
) -> None:
    """Handles toggling whether the model will think or not."""
    temp_config = read_temp_config()

    thinking = temp_config.get("thinking", None)
    if thinking is None:
        logger.error("Thinking key missing!")
        return

    if not thinking:
        logger.info("Enabled thinking.")
        await ctx.send("Enabled thinking.")
        save_temp_config(thinking=True)
        return

    logger.info("Disabled thinking.")
    await ctx.send("Disabled thinking.")
    save_temp_config(thinking=False)


async def _handle_thinking_budget(
    ctx: commands.Context,
    thinking_budget: int | None,
) -> None:
    """Handles changing the thinking budget."""
    temp_config = read_temp_config()

    budget = temp_config.get("thinking_budget", None)
    if budget is None:
        logger.error("thinking_budget key missing!")
        return

    if thinking_budget is None:
        logger.info("Set thinking budget to auto.")
        await ctx.send("Thinking budget is set to auto (turned off).")
        save_temp_config(thinking_budget=0)
        return

    logger.info(f"Thinking budget is {thinking_budget}.")
    await ctx.send(f"Thinking budget is now {thinking_budget}.")
    save_temp_config(thinking_budget=thinking_budget)


async def _handle_toggle_uwu(
    ctx: commands.Context,
    initial_state: dict,
) -> None:
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



def setup_toggle_command(client: Bot, initial_state: dict[str, Any]) -> None:
    """Set up the toggle command."""
    @client.hybrid_command(name="toggle")
    @commands.has_permissions(manage_messages=True)
    @app_commands.choices(toggles=[
        app_commands.Choice(name="System Prompt", value="sys"),
        app_commands.Choice(name="Model", value="model"),
        app_commands.Choice(name="Tools", value="tools"),
        app_commands.Choice(name="Thinking", value="thinking"),
        app_commands.Choice(name="Thinking Budget", value="thinking_budget"),
        app_commands.Choice(name="UwU", value="uwu"),
    ])
    async def toggle(
            ctx: commands.Context,
            toggles: str,
            index: int | None = None,
            thinking_budget: int | None = None,
    ) -> None:
        """Toggle system prompt, model, or tools for the bot.

        Args:
            ctx: The context of the command invocation.
            toggles: What to toggle.
            index: The index to set. Optional.
            thinking_budget: The thinking budget to set if what you're going to set
                             is the thinking budget.
        """
        toggle_handlers = {
            "sys": lambda: _handle_toggle_sys_prompt(ctx, initial_state, index),
            "model": lambda: _handle_toggle_model(ctx, client, initial_state, index),
            "tools": lambda: _handle_toggle_tools(ctx, initial_state, index),
            "thinking": lambda: _handle_toggle_thinking(ctx),
            "thinking_budget": lambda: _handle_thinking_budget(ctx, thinking_budget),
            "uwu": lambda : _handle_toggle_uwu(ctx, initial_state),
        }

        handler = toggle_handlers.get(toggles)
        if handler:
            await handler()
            return

        logger.warning(f"Invalid toggle value received: {toggles}")
        await ctx.reply("Invalid toggle option specified.", ephemeral=True)
