from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from google.genai import Client, errors

from packages.maps import MAX_MESSAGE_LENGTH, YOUTUBE_PATTERN
from packages.tools.memory import load_memory
from packages.utilities.file_utils import save_temp_config
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
    from discord.ext import commands
    from google.genai.types import (
        Content,
        Tool,
    )

latest_token_count = 0
ctx_glob = None # Only this file will modify ctx_glob
memory = []
logger = logging.getLogger(__name__)


def save_memory(history: list[Content]) -> None:
    """Save the history to a global variable."""
    global memory
    memory = history


def clear_memory() -> None:
    """Clear global variable."""
    memory.clear()


def get_memory() -> list:
    """Get the global variable."""
    return memory


async def handle_clear(ctx: commands.Context) -> None:
    """Handle the clear command.

    Args:
        ctx: the context of the command invocation

    """
    global latest_token_count
    latest_token_count = 0
    if ctx.author.guild_permissions.administrator:
        clear_memory()
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
    return

def prompt(tools: list[Tool], genai_client: Client) -> Callable:
    """A prompt wrapper function.

    Args:
        tools: A list of tools for the model to use.
               E.g. Code Execution or custom function calls.
        genai_client: The genai client to use.

    Returns:
        A prompt command.
    """
    async def command(ctx: commands.Context) -> None:
        global ctx_glob, latest_token_count
        file_names = []

        try:
            curr_memory = get_memory()
            message = ctx.message.content.replace(f"<@{ctx.bot.user.id}>", "").strip()
            if await validate_invocation(ctx, message):
                return
            now = datetime.now(timezone.utc)
            formatted_time = now.strftime("%A, %B %d, %Y %H:%M:%S UTC")
            model, api_config, safety_setting, temp_config = prepare_api_config(tools)

            async with ctx.typing():
                if message.lower() == "{clear}":
                    await handle_clear(ctx)
                    return

                chat = create_chat(genai_client, model, api_config, curr_memory)
                ctx_glob = ctx

                logger.info(f"Received Input With Prompt: {message}")
                final_prompt = [YOUTUBE_PATTERN.sub("", message)]
                attachment_file_names = await process_attachments(
                    ctx,
                    genai_client,
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
                latest_token_count = response.usage_metadata.total_token_count

                save_memory(chat._curated_history)

                logger.info("Got Response.")

                output_file_names = await process_response_parts(
                    ctx,
                    candidates,
                    finish_reason,
                    temp_config,
                    tools,
                )

                file_names.extend(output_file_names)

        except (
            errors.ClientError,
        ) as e:
            message = e
            try:
                message = f"{e.code} {e.status}: {e.message}."
            except AttributeError:
                pass

            await send_long_message(
                ctx,
                "Something went wrong on our side. "
                f"\n{message}"
                if not isinstance(message, Exception) else
                "Something went wrong on our side. "
                "Please submit a bug report at the GitHub repo for this bot, "
                f"or ping the creator.\n```{message}```",
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
    return command
