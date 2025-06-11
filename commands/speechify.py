from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

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

logger = logging.getLogger(__name__)


def speechify(genai_client: Client) -> commands.HybridCommand:
    """Set up the imagen command.

    Args:
        genai_client: the google.genai Client object.

    """

    @commands.hybrid_command(name="speechify")
    @app_commands.choices(
        voice=[
            app_commands.Choice(
                name=f"{voice["name"]} ({voice["personality"]})",
                value=voice["name"].lower(),
            )
            for voice in TTS_VOICES
        ],
    )
    async def command(
            ctx: commands.Context,
            *,
            prompt: str,
            voice: str | None = None,
            model: str | None = "gemini-2.5-flash-preview-tts",
    ) -> None:
        """Generates a text-to-speech audio file from a prompt.

        Args:
            ctx: The context of the command invocation
            prompt: The prompt to send Gemini
            voice: The voice of the speech
            model: The TTS model to use
        """
        try:
            async with ctx.typing():
                config = generate_audio_config(voice)
                # ? Do I really need this as this thing outputs only one file?
                file_names = []

                response = await genai_client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )

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
            logger.exception("An exception happened.")

        finally:
            try:
                for file in file_names:
                    Path(file).unlink()
                    logger.info(f"Deleted {file} at local server.")
            except UnboundLocalError:
                pass

    return command
