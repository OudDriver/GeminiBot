from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from bot.setup import DEFAULT_TOOLS_MAP
from packages.utilities.file_utils import read_temp_config, save_temp_config

if TYPE_CHECKING:
    from main import GeminiBot

logger = logging.getLogger(__name__)


class ToggleCog(commands.Cog, name="Toggle"):
    """A cog for toggling various bot configurations like system prompts, models, and tools."""

    def __init__(self, bot: "GeminiBot"):
        self.bot = bot

    async def _handle_toggle_sys_prompt(self, ctx: commands.Context, index: int | None) -> None:
        """Handles toggling the system prompt."""
        # Get static list of prompts from bot's main config
        prompts = self.bot.config.get("SystemPrompts", [])
        # Get current state from temp config
        temp_config = read_temp_config()

        if not prompts:
            await ctx.reply("No system prompts available to switch to.", ephemeral=True)
            return

        max_index = len(prompts)
        if index is not None and not (1 <= index <= max_index):
            await ctx.reply(
                (
                    f"Index out of bounds! Please use a number between 1 and {max_index}. "
                    f"Use the !list command for more information."
                ),
                ephemeral=True,
            )
            return

        current_index = temp_config.get("current_sys_prompt_index", 0)
        if index is None:
            new_index = (current_index + 1) % max_index
        else:
            new_index = index - 1

        selected_prompt = prompts[new_index]
        system_prompt_name = selected_prompt.get("Name", f"Prompt {new_index + 1}")
        system_prompt_data = selected_prompt.get("SystemPrompt", "")

        # Update temp config with new state (using kwargs for save_temp_config)
        save_temp_config(
            system_prompt_data=system_prompt_data,
            system_prompt_name=system_prompt_name,
            current_sys_prompt_index=new_index,
        )
        logger.info(f"Switched to system prompt: {system_prompt_name}")
        await ctx.send(f"Using system prompt: {system_prompt_name}.")


    async def _handle_toggle_model(self, ctx: commands.Context, index: int | None) -> None:
        """Handles toggling the model."""
        models = self.bot.config.get("ModelNames", {})
        model_options = list(models.keys())
        temp_config = read_temp_config()

        if not model_options:
            await ctx.reply("No models available to switch to.", ephemeral=True)
            return

        max_index = len(model_options)
        if index is not None and not (1 <= index <= max_index):
            await ctx.reply(
                (
                    f"Index out of bounds! Please use a number between 1 and {max_index}. "
                    f"Use the !list command for more information."
                ),
                ephemeral=True,
            )
            return

        current_model_id = temp_config.get("model", None)
        try:
            current_index = model_options.index(current_model_id) if current_model_id else 0
        except ValueError: # Current model ID not found in available options
            current_index = 0

        if index is None:
            new_index = (current_index + 1) % max_index
        else:
            new_index = index - 1

        selected_model_option = model_options[new_index]

        # Update temp config with new state
        save_temp_config(
            model=selected_model_option,
            current_model_index=new_index,
        )

        friendly_name = models.get(selected_model_option, selected_model_option)

        logger.info(f"Switched to model: {friendly_name}")
        await ctx.send(f"Switched to model: {friendly_name}.")
        try:
            await self.bot.change_presence(
                activity=discord.CustomActivity(
                    name=f"Hello there! I am using {friendly_name}",
                ),
            )
        except Exception:
            logger.exception("Failed to update presence.")


    async def _handle_toggle_tools(self, ctx: commands.Context, index: int | None) -> None:
        """Handles toggling the active toolset."""
        # Get static tool definitions from bot's main config
        temp_config = read_temp_config()

        max_index = len(DEFAULT_TOOLS_MAP)
        if index is not None and not (1 <= index <= max_index):
            await ctx.reply(
                (
                    f"Index out of bounds! Please use a number between 1 and {max_index}. "
                    f"Use the !list command for more information."
                ),
                ephemeral=True,
            )
            return

        current_active_tools_name = temp_config.get("active_tools_name", None)
        try:
            keys_list = list(DEFAULT_TOOLS_MAP.keys())
            current_index = keys_list.index(current_active_tools_name) if current_active_tools_name else 0
        except ValueError:  # Current toolset name not found
            current_index = 0

        new_index = (current_index + 1) % max_index if index is None else index - 1

        keys_list = list(DEFAULT_TOOLS_MAP.keys())
        tool_name = keys_list[new_index]

        save_temp_config(
            active_tools_index=new_index,
            active_tools_name=tool_name,
        )

        logger.info(f"Switched to toolset: {tool_name}")
        await ctx.send(f"Switched to toolset: {tool_name}.")


    @staticmethod
    async def _handle_toggle_thinking(ctx: commands.Context) -> None:
        """Handles toggling whether the model will think or not."""
        temp_config = read_temp_config()
        thinking = temp_config.get("thinking", False)

        if not thinking:
            logger.info("Enabled thinking.")
            await ctx.send("Enabled thinking.")
            save_temp_config(thinking=True)
        else:
            logger.info("Disabled thinking.")
            await ctx.send("Disabled thinking.")
            save_temp_config(thinking=False)


    @staticmethod
    async def _handle_thinking_budget(ctx: commands.Context, thinking_budget: int | None) -> None:
        """Handles changing the thinking budget."""
        temp_config = read_temp_config() # Read to show current state

        if thinking_budget is None:
            logger.info("Set thinking budget to auto.")
            await ctx.send(f"Thinking budget is set to auto (currently {temp_config.get('thinking_budget', 'N/A')}).")
            save_temp_config(thinking_budget=0) # 0 for auto/off based on `setup.py` refactor
        elif thinking_budget < 0:
            await ctx.send("Thinking budget cannot be negative.", ephemeral=True)
            return
        else:
            logger.info(f"Thinking budget is {thinking_budget}.")
            await ctx.send(f"Thinking budget is now {thinking_budget}.")
            save_temp_config(thinking_budget=thinking_budget)


    @staticmethod
    async def _handle_toggle_uwu(ctx: commands.Context) -> None:
        """Handles toggling the UwUifier."""
        temp_config = read_temp_config()
        current_uwu_status = temp_config.get("current_uwu_status", False)

        new_uwu_status = not current_uwu_status
        # Only save the 'current_uwu_status' key. The original had model/system_prompt, which is bad.
        save_temp_config(current_uwu_status=new_uwu_status)

        if new_uwu_status:
            await ctx.reply(
                "Enabled Uwuifier. Beware that asking it for code will not work.",
            )
            logger.info("Enabled Uwuifier.")
        else:
            await ctx.reply("Disabled Uwuifier.")
            logger.info("Disabled Uwuifier.")

    @commands.hybrid_command(name="toggle")
    @commands.has_permissions(manage_messages=True)
    @app_commands.choices(toggles=[
        app_commands.Choice(name="System Prompt", value="sys"),
        app_commands.Choice(name="Model", value="model"),
        app_commands.Choice(name="Tools", value="tools"),
        app_commands.Choice(name="Thinking", value="thinking"),
        app_commands.Choice(name="Thinking Budget", value="thinking_budget"),
        app_commands.Choice(name="UwU", value="uwu"),
    ])
    async def toggle_command(
            self,
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
            "sys": lambda: self._handle_toggle_sys_prompt(ctx, index),
            "model": lambda: self._handle_toggle_model(ctx, index),
            "tools": lambda: self._handle_toggle_tools(ctx, index),
            "thinking": lambda: self._handle_toggle_thinking(ctx),
            "thinking_budget": lambda: self._handle_thinking_budget(ctx, thinking_budget),
            "uwu": lambda: self._handle_toggle_uwu(ctx),
        }

        handler = toggle_handlers.get(toggles)
        if handler:
            await handler()
            return

        logger.warning(f"Invalid toggle value received: {toggles}")
        await ctx.reply("Invalid toggle option specified.", ephemeral=True)

async def setup(bot: "GeminiBot"):
    """Adds the ToggleCog to the bot."""
    await bot.add_cog(ToggleCog(bot))