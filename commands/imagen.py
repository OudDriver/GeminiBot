from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
from discord import app_commands
from discord.ext import commands
from google.genai.types import (
    GenerateImagesConfig,
)

from packages.utilities.general_utils import (
    generate_unique_file_name,
    send_image,
    send_long_message,
)

if TYPE_CHECKING:
    from google.genai import Client

MAX_MESSAGE_LENGTH = 2000

def imagen(genai_client: Client) -> commands.HybridCommand:
    """Set up the imagen command.

    Args:
        genai_client: the google.genai client.

    """
    logger = logging.getLogger(__name__)

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
    async def command(
            ctx: commands.Context,
            *,
            prompt: str,
            aspect_ratio: str | None=None,
    ) -> None:
        """Generate an image from a prompt.

        Args:
            ctx: The context of the command invocation
            prompt: The prompt to send Imagen
            aspect_ratio: The aspect ratio of the generated image

        """
        try:
            async with ctx.typing():
                logger.info(f"Got Image Generation Prompt {prompt}")

                config = GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                )

                response = await genai_client.aio.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=prompt,
                    config=config,
                )

                file_names = []

                logger.info("Got Generated Image.")
                for generated_image in response.generated_images:
                    file_name = "./temp/" + generate_unique_file_name("png")
                    image = generated_image.image.image_bytes

                    try:
                        async with await anyio.open_file(file_name,"wb") as f:
                            await f.write(image)
                    except Exception:
                        logger.exception(
                            "An unexpected error happened "
                            "while trying to save image.",
                        )
                        return

                    file_names.append(file_name)
                    await send_image(ctx, file_name)

        except Exception as e:
            await send_long_message(
                ctx, f"A general error happened! `{e}`", MAX_MESSAGE_LENGTH,
            )
            logger.exception(traceback.format_exc())

        finally:
            try:
                for file in file_names:
                    file_to_del = Path(file)
                    file_to_del.unlink()
                    logger.info(f"Deleted {file_to_del.name} at local server")
            except UnboundLocalError:
                pass

    return command
