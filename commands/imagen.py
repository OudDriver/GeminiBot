from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import discord
from discord import app_commands
from discord.ext import commands
from google.genai.types import GenerateImagesConfig

from packages.maps import MAX_MESSAGE_LENGTH
from packages.utilities.general_utils import (
    generate_unique_file_name,
    send_file,
    send_long_message,
)

if TYPE_CHECKING:
    from google.genai import Client
    from main import GeminiBot

logger = logging.getLogger(__name__)


class ImagenCog(commands.Cog, name="Imagen"):
    """A cog for generating images using an AI model."""

    def __init__(self, bot: "GeminiBot", genai_client: Client):
        self.bot = bot
        self.genai_client = genai_client

    @commands.hybrid_command(name="imagen")
    @app_commands.choices(
        aspect_ratio=[
            app_commands.Choice(name="1:1", value="1:1"),
            app_commands.Choice(name="3:4", value="3:4"),
            app_commands.Choice(name="4:3", value="4:3"),
            app_commands.Choice(name="9:16", value="9:16"),
            app_commands.Choice(name="16:9", value="16:9"),
        ],
    )
    async def imagen_command(
            self,
            ctx: commands.Context,
            *,
            prompt: str,
            aspect_ratio: str | None = None,
    ) -> None:
        """Generate an image from a prompt.

        Args:
            ctx: The context of the command invocation
            prompt: The prompt to send Imagen
            aspect_ratio: The aspect ratio of the generated image
        """
        file_names = [] # Initialize here to ensure it's always defined for finally block
        try:
            async with ctx.typing():
                logger.info(f"Got Image Generation Prompt {prompt}")

                config = GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                )

                response = await self.genai_client.aio.models.generate_images(
                    model="imagen-3.0-generate-002", # Model is hardcoded
                    prompt=prompt,
                    config=config,
                )

                if not response.generated_images:
                    await send_long_message(
                        ctx,
                        "Image generation failed: No images returned.",
                        MAX_MESSAGE_LENGTH,
                    )
                    return

                logger.info("Got Generated Image.")
                for generated_image in response.generated_images:
                    if not generated_image.image or not generated_image.image.image_bytes:
                        logger.warning("Generated image part missing image_bytes.")
                        continue # Skip if image data is missing

                    file_name = "./temp/" + generate_unique_file_name("png")
                    image_bytes = generated_image.image.image_bytes

                    async with await anyio.open_file(file_name,"wb") as f:
                        await f.write(image_bytes)

                    file_names.append(file_name)
                    await send_file(ctx, file_name)

        except Exception as e:
            await send_long_message(
                ctx,
                f"A general error happened! `{e}`",
                MAX_MESSAGE_LENGTH,
            )
            logger.exception(f"An exception happened during imagen command: {traceback.format_exc()}")

        finally:
            for file in file_names: # file_names is always defined now
                try:
                    Path(file).unlink()
                    logger.info(f"Deleted {file} at local server")
                except OSError as e:
                    logger.warning(f"Error deleting file {file}: {e}")
                except Exception as e:
                    logger.exception(f"Unexpected error during file cleanup for {file}.")

async def setup(bot: "GeminiBot"):
    """Adds the ImagenCog to the bot."""
    await bot.add_cog(ImagenCog(bot, bot.genai_client))