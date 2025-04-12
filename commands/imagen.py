import traceback
import os
import logging

from discord import app_commands
from discord.ext import commands
from google.genai.types import (
    GenerateImagesConfig,
)
from google.genai import Client

from packages.utils import (
    send_long_message,
    send_image,
    generate_unique_file_name,
)

MAX_MESSAGE_LENGTH = 2000

def imagen(genai_client: Client):
    @commands.hybrid_command(name="imagen")
    @app_commands.choices(
        aspect_ratio=[
            app_commands.Choice(name="1:1", value="1:1"),
            app_commands.Choice(name="3:4", value="3:4"),
            app_commands.Choice(name="4:3", value="4:3"),
            app_commands.Choice(name="9:16", value="9:16"),
            app_commands.Choice(name="16:9", value="16:9")
        ]
    )
    async def command(ctx: commands.Context, *, prompt: str, aspect_ratio: str | None=None):
        """
        Generates a response. Supports file inputs and YouTube links.

        Args:
            ctx: The context of the command invocation
            prompt: The prompt to send Imagen
            aspect_ratio: The aspect ratio of the generated image
        """
        try:
            async with ctx.typing():
                logging.info(f"Got Image Generation Prompt {prompt}")

                config = GenerateImagesConfig(number_of_images=1, aspect_ratio=aspect_ratio)

                response = await genai_client.aio.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=config
                )

                file_names = []

                logging.info("Got Generated Image.")
                for generated_image in response.generated_images:
                    file_name = "./temp/" + generate_unique_file_name("png")
                    image = generated_image.image.image_bytes

                    try:
                        with open(file_name,"wb") as f:
                            f.write(image)
                    except Exception as e:
                        logging.error(e)
                        return

                    file_names.append(file_name)
                    await send_image(ctx, file_name)

        except Exception as e:
            await send_long_message(
                ctx, f"A general error happened! `{e}`", MAX_MESSAGE_LENGTH
            )
            logging.error(traceback.format_exc())

        finally:
            try:
                for file in file_names:
                    os.remove(file)
                    logging.info(f"Deleted {os.path.basename(file)} at local server")
            except UnboundLocalError:
                pass

    return command
