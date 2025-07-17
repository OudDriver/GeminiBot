from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

import discord
from discord.ext import commands
from google.genai import errors
from google.genai.types import Content, Tool

from packages.maps import MAX_MESSAGE_LENGTH, YOUTUBE_PATTERN
from packages.tools.memory import load_memory
from packages.utilities.file_utils import save_temp_config, read_temp_config
from packages.utilities.general_utils import send_long_message
from packages.utilities.prompt_utils import (
    cleanup_files,
    create_chat,
    prepare_api_config,
    prepend_author_info,
    process_attachments,
    process_response_parts,
    process_youtube_links,
    send_message_and_handle_status,
    validate_invocation,
)

if TYPE_CHECKING:
    from google.genai import Client
    from main import GeminiBot

logger = logging.getLogger(__name__)


class PromptCog(commands.Cog, name="Prompt"):
    """A cog for handling AI prompts and chat memory."""

    def __init__(self, bot: "GeminiBot", genai_client: Client):
        self.bot = bot
        self.genai_client = genai_client
        self.memory: List[Content] = []

    def _save_memory(self, history: List[Content]) -> None:
        """Save the history to the cog's memory."""
        self.memory = history

    def _clear_memory(self) -> None:
        """Clear the cog's memory."""
        self.memory.clear()

    def _get_memory(self) -> List:
        """Get the cog's memory."""
        return self.memory

    async def _handle_clear(self, ctx: commands.Context) -> None:
        """Handle the clear command logic."""
        self.bot.latest_token_count = 0
        if ctx.author.guild_permissions.administrator:
            self._clear_memory()
            save_temp_config(tool_use={})
            await ctx.reply(
                "Alright, I have cleared my context. What are we gonna talk about?",
            )
            logger.info("Cleared context.")
            return
        await ctx.reply(
            "You don't have the necessary permissions for this!",
            ephemeral=True,
        )

    # REMOVED: @commands.hybrid_command(name="prompt")
    async def handle_ai_interaction(self, ctx: commands.Context) -> None: # Renamed from prompt_command
        """Handles AI interaction based on a Discord message context (triggered by mention/reply)."""
        file_names = []

        try:
            curr_memory = self._get_memory()
            # This line is crucial for extracting the user's message when mentioned/replied
            message = ctx.message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            if await validate_invocation(ctx, message):
                return
            now = datetime.now(timezone.utc)
            formatted_time = now.strftime("%A, %B %d, %Y %H:%M:%S UTC")

            # Get active tools based on what's set in temp_config
            temp_config = read_temp_config()
            active_tools_name = temp_config.get("active_tools_name", "Nothing")
            # Lookup the actual tool definitions from bot's static config
            configured_tools = self.bot.config.get("Tools", {})
            active_tools: List[Tool] = configured_tools.get(active_tools_name, [])

            # `prepare_api_config` will read model, safety, thinking from temp_config
            model, api_config, safety_setting, temp_config_for_prompt = prepare_api_config(active_tools)
            # Use `temp_config_for_prompt` from `prepare_api_config` for consistency, as it's fresh.

            async with ctx.typing():
                if message.lower() == "{clear}":
                    await self._handle_clear(ctx)
                    return

                chat = create_chat(self.genai_client, model, api_config, curr_memory)

                logger.info(f"Received Input With Prompt: {message}")
                final_prompt = [YOUTUBE_PATTERN.sub("", message)]
                attachment_file_names = await process_attachments(
                    ctx,
                    self.genai_client,
                    final_prompt,
                )

                file_names.extend(attachment_file_names)
                await prepend_author_info(ctx, final_prompt, formatted_time)

                if not curr_memory:
                    mem = load_memory()
                    if mem:
                        final_prompt.insert(0, f"This is the memory you saved: {mem}")

                process_youtube_links(message, final_prompt)

                if model == "gemini-2.0-flash-exp-image-generation":
                    final_prompt = final_prompt[-1]

                logger.info(f"Got Final Prompt {final_prompt}")

                response_result = await send_message_and_handle_status(
                    chat,
                    final_prompt,
                    ctx,
                    safety_setting,
                )

                response, candidates, first_candidate, finish_reason = response_result
                self.bot.latest_token_count = response.usage_metadata.total_token_count

                self._save_memory(chat._curated_history)

                logger.info("Got Response.")

                output_file_names = await process_response_parts(
                    ctx,
                    candidates,
                    finish_reason,
                    temp_config_for_prompt,
                    active_tools,
                )

                file_names.extend(output_file_names)

        except errors.ClientError as e:
            message_str = f"{e.code} {e.status}: {e.message}." if hasattr(e, 'code') else str(e)
            await send_long_message(
                ctx,
                f"Something went wrong on our side.\n{message_str}",
                MAX_MESSAGE_LENGTH,
            )
            logger.exception("An error happened at our side.")

        except (errors.ServerError, errors.APIError) as e:
            await send_long_message(
                ctx,
                f"Something went wrong on Google's end / Gemini. "
                f"Please wait for a while and try again.\n```{e}```",
                MAX_MESSAGE_LENGTH,
            )
            logger.exception(
                "An error happened at Gemini's side (or rather a general API error).",
            )

        except Exception as e:
            await send_long_message(
                ctx,
                f"Something went wrong. "
                f"Please review the error and maybe submit a bug report.\n```{e}```",
                MAX_MESSAGE_LENGTH,
            )
            logger.exception("An unexpected error happened.")

        finally:
            cleanup_files(file_names)

async def setup(bot: "GeminiBot"):
    """Adds the PromptCog to the bot."""
    await bot.add_cog(PromptCog(bot, bot.genai_client))