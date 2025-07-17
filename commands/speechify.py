from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from packages.maps import MAX_MESSAGE_LENGTH, TTS_VOICES
from packages.utilities.file_utils import save_wave_file
from packages.utilities.general_utils import (
    generate_unique_file_name,
    send_file,
    send_long_message,
)
from packages.utilities.prompt_utils import generate_audio_config

if TYPE_CHECKING:
    from google.genai import Client
    from main import GeminiBot

logger = logging.getLogger(__name__)


class SpeechifyCog(commands.Cog, name="Speechify"):
    """A cog for generating text-to-speech audio."""

    def __init__(self, bot: "GeminiBot", genai_client: Client):
        self.bot = bot
        self.genai_client = genai_client

    @commands.hybrid_command(name="speechify")
    @app_commands.choices(
        voice=[
            app_commands.Choice(
                name=f"{voice['name']} ({voice['personality']})",
                value=voice["name"].lower(),
            )
            for voice in TTS_VOICES
        ],
    )
    async def speechify_command(
            self,
            ctx: commands.Context,
            *,
            prompt: str,
            voice: str | None = None,
            model: str | None = "gemini-2.5-flash-preview-tts", # Default model
    ) -> None:
        """Generates a text-to-speech audio file from a prompt.

        Args:
            ctx: The context of the command invocation
            prompt: The prompt to send Gemini
            voice: The voice of the speech
            model: The TTS model to use
        """
        file_names = [] # Initialize here to ensure it's always defined for finally block
        try:
            async with ctx.typing():
                config = generate_audio_config(voice)

                response = await self.genai_client.aio.models.generate_content(
                    model=model,
                    contents=[prompt],
                    config=config,
                )

                if not response.candidates or not response.candidates[0].content:
                    logger.error(f"No content generated for prompt: {prompt}")
                    await ctx.send(
                        "There was no content generated from the model. "
                        "Revise your prompt and try again!",
                    )
                    return

                # Check for inline_data and data within parts
                if (
                        not response.candidates[0].content.parts
                        or not response.candidates[0].content.parts[0].inline_data
                        or not response.candidates[0].content.parts[0].inline_data.data
                ):
                    logger.error(f"Response did not contain expected audio data structure: {response.candidates[0]}")
                    await ctx.send(
                        "The model did not return audio data in the expected format. "
                        "Please try again or contact support.",
                    )
                    return


                data = response.candidates[0].content.parts[0].inline_data.data

                logger.info("Got audio file.")
                file_name = "./temp/" + generate_unique_file_name("wav")

                save_wave_file(file_name, data)
                file_names.append(file_name)

                await send_file(ctx, file_name)

        except Exception as e:
            await send_long_message(
                ctx,
                f"Something happened.\n```{e}```",
                MAX_MESSAGE_LENGTH,
            )
            logger.exception("An exception happened during speechify command.")

        finally:
            for file in file_names: # file_names is always defined now
                try:
                    Path(file).unlink()
                    logger.info(f"Deleted {file} at local server.")
                except OSError as e:
                    logger.warning(f"Error deleting file {file}: {e}")
                except Exception as e:
                    logger.exception(f"Unexpected error during file cleanup for {file}.")


async def setup(bot: "GeminiBot"):
    """Adds the SpeechifyCog to the bot."""
    await bot.add_cog(SpeechifyCog(bot, bot.genai_client))