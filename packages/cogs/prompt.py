from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from discord.ext import commands
from google.genai import errors

from packages.maps import IMAGE_GENERATION_MODELS, MAX_MESSAGE_LENGTH, YOUTUBE_PATTERN
from packages.tools.memory import load_memory
from packages.utilities.file_utils import save_temp_config
from packages.utilities.general_utils import send_long_message
from packages.utilities.prompt_utils import (
    PromptData,
    cleanup_files,
    create_chat,
    execute_ai_chat,
    get_active_tools,
    prepare_api_config,
    prepend_author_info,
    process_attachments,
    process_response_parts,
    process_youtube_links,
    validate_invocation,
)

if TYPE_CHECKING:
    from google.genai import Client
    from google.genai.chats import AsyncChat
    from google.genai.types import (
        Content,
        FinishReason,
        GenerateContentResponse,
    )

    from main import GeminiBot



logger = logging.getLogger(__name__)
ctx_glob = None # screw it

class PromptCog(commands.Cog, name="Prompt"):
    """A cog for handling AI prompts and chat memory."""

    def __init__(self, bot: GeminiBot, genai_client: Client) -> None:
        """Initializes the cog."""
        self.bot = bot
        self.genai_client = genai_client
        self.memory: list[Content] = []

    def _save_memory(self, history: list[Content]) -> None:
        """Save the history to the cog's memory."""
        self.memory = history

    def _clear_memory(self) -> None:
        """Clear the cog's memory."""
        self.memory.clear()

    def _get_memory(self) -> list:
        """Get the cog's memory."""
        return self.memory

    async def _handle_clear(self, ctx: commands.Context) -> None:
        """Handle the clear command logic."""
        self.bot.latest_token_count = 0
        if ctx.author.guild_permissions.administrator:
            self._clear_memory()
            save_temp_config(tool_call={})
            await ctx.reply(
                "Alright, I have cleared my context. What are we gonna talk about?",
            )
            logger.info("Cleared context.")
            return
        await ctx.reply(
            "You don't have the necessary permissions for this!",
            ephemeral=True,
        )

    async def _prepare_prompt_data(self, ctx: commands.Context) -> PromptData | None:
        """Parses the context, validates, and prepares API configurations."""
        message = ctx.message.content.replace(f"<@{self.bot.user.id}>", "").strip()

        if await validate_invocation(ctx, message):
            return None

        now = datetime.now(timezone.utc)
        active_tools = get_active_tools()
        model, api_config, safety_setting, temp_config = prepare_api_config(
            active_tools,
        )

        return PromptData(
            ctx=ctx,
            clean_message=message,
            model=model,
            api_config=api_config,
            safety_setting=safety_setting,
            temp_config_for_prompt=temp_config,
            active_tools=active_tools,
            formatted_time=now.strftime("%A, %B %d, %Y %H:%M:%S UTC"),
        )

    async def _build_final_prompt(self, data: PromptData) -> tuple[list, list[str]]:
        """Constructs the final prompt list and collects attachment file names."""
        final_prompt = [YOUTUBE_PATTERN.sub("", data.clean_message)]
        attachment_files = await process_attachments(
            data.ctx,
            self.genai_client,
            final_prompt,
        )

        await prepend_author_info(data.ctx, final_prompt, data.formatted_time)

        if not self._get_memory():
            mem = load_memory()
            if mem:
                final_prompt.insert(0, f"This is the memory you saved: {mem}")

        process_youtube_links(data.clean_message, final_prompt)

        if data.model in IMAGE_GENERATION_MODELS:
            return final_prompt[-1], attachment_files

        return final_prompt, attachment_files

    async def _process_ai_response(
        self,
        response: GenerateContentResponse,
        finish_reason: FinishReason,
        chat: AsyncChat,
        data: PromptData,
    ) -> list[str]:
        """Processes the AI's response, saves memory, and handles output files."""
        self.bot.latest_token_count = response.usage_metadata.total_token_count
        self._save_memory(chat._curated_history)

        return await process_response_parts(
            data.ctx,
            response.candidates,
            finish_reason,
            data.temp_config_for_prompt,
            data.active_tools,
        )

    async def handle_interaction(self, ctx: commands.Context) -> None:
        """Orchestrates the AI interaction process."""
        global ctx_glob

        all_files_to_clean = []
        ctx_glob = ctx
        try:
            # 1. Preparation
            prompt_data = await self._prepare_prompt_data(ctx)
            if not prompt_data:
                return # Validation failed or was a command like {clear}

            async with ctx.typing():
                # Handles clear command
                if prompt_data.clean_message.lower() == "{clear}":
                    await self._handle_clear(ctx)
                    return

                # 2. Prompt Construction
                final_prompt, attachment_files = await self._build_final_prompt(
                    prompt_data,
                )
                all_files_to_clean.extend(attachment_files)
                logger.info(f"Built Final Prompt: {final_prompt}")

                # 3. API Execution
                chat = create_chat(
                    self.genai_client,
                    prompt_data.model,
                    prompt_data.api_config,
                    self._get_memory(),
                )

                response, finish_reason = await execute_ai_chat(
                    chat,
                    final_prompt,
                    prompt_data,
                )

                output_files = await self._process_ai_response(
                    response,
                    finish_reason,
                    chat,
                    prompt_data,
                )
                all_files_to_clean.extend(output_files)

        except errors.ClientError as e:
            message_str = f"{e.code} {e.status}: {e.message}." \
                if hasattr(e, "code") else str(e)
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
            cleanup_files(all_files_to_clean)

async def setup(bot: GeminiBot) -> None:
    """Adds the PromptCog to the bot."""
    await bot.add_cog(PromptCog(bot, bot.genai_client))
