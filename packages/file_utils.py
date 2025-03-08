from google.genai.types import File
from google.genai import Client
import time
import logging
import asyncio

from packages.utils import generate_unique_file_name

def check_for_file_active(uploaded_file: File):
    """
    Checks if the uploaded file is active on Google servers.
    """
    status = uploaded_file.state
    return status == "ACTIVE"


async def wait_for_file_active(uploaded_file_to_check):
    """
    Waits until the uploaded file becomes active on Google servers.
    """
    start_time = time.monotonic()
    timeout = 30

    try:
        while not check_for_file_active(uploaded_file_to_check):
            if time.monotonic() - start_time >= timeout:
                logging.warning(
                    f"Timeout while waiting for file {uploaded_file_to_check.name} to become active. Skipping Check")
                return

            await asyncio.sleep(1)

    except Exception as e:
        logging.error(f"Error while waiting for file active! {e}.")


async def handle_attachment(attachment, client: Client):
    try:
        file_extension = attachment.filename.split(".")[-1]
        unique_file_name = generate_unique_file_name(file_extension)
        file_name = f"./temp/{unique_file_name}"

        await attachment.save(file_name)
        logging.info(f"Saved {attachment.content_type.split('/')[0]} {file_name}")

        file_names = []
        uploaded_files = []

        file_names.append(file_name)
        uploaded_file = await asyncio.to_thread(client.files.upload, file=file_name)
        uploaded_files.append(uploaded_file)

        logging.info(f"Uploaded {uploaded_file.display_name} as {uploaded_file.name}")

        return file_names, uploaded_files
    except Exception as e:
        logging.error(f"Error in handleAttachment: {e}")
        return [], []  # Return empty lists to indicate failure