from pytubefix import YouTube
import asyncio, re
import google.generativeai as genai
import logging
import os
import time

from packages.utils import generate_unique_file_name

def download_video(link: str):
    """
    Downloads separate video and audio streams from a YouTube link and returns their paths.
    """
    video = YouTube(link).streams.first().download(output_path='./temp', filename=generate_unique_file_name('mp4'))

    return video

def search_regex(pattern: str, text: str):
    """
    Searches for a regex pattern in a text and returns the match if found.
    """
    match = re.search(pattern, text)
    if match:
        link = match.group(0)
        return link
    return None

def check_for_file_active(uploaded_file):
    """
    Checks if the uploaded file is active on Google servers.
    """
    status = genai.get_file(uploaded_file.name).state
    return status == 2

async def wait_for_file_active(uploaded_file_to_check):
    """
    Waits until the uploaded file becomes active on Google servers.
    """
    start_time = time.monotonic()
    timeout = 30

    try:
        while not check_for_file_active(uploaded_file_to_check):
            if time.monotonic() - start_time >= timeout:
                logging.warning(f"Timeout while waiting for file {uploaded_file_to_check.name} to become active. Skipping Check")
                return 

            await asyncio.sleep(1)  
                
    except Exception as e:
        logging.error(f"Error while waiting for file active! {e}.")
        
async def handle_youtube(link):
    try:
        video_file = await asyncio.to_thread(download_video, link.group(0))
        
        logging.info(f"Downloaded The Video {os.path.basename(video_file)}")
        
        file_names = []
        uploaded_files = []
        
        file_names.extend([video_file])
        uploaded_youtube_file = await asyncio.to_thread(genai.upload_file, video_file)
        uploaded_files.append(uploaded_youtube_file)
        
        logging.info(f"Uploaded {uploaded_youtube_file.display_name} as {uploaded_youtube_file.name}")
        
        return file_names, uploaded_files
    except Exception as e:
        logging.error(f"Error in handleYoutube: {e}")
        return [], [] # Return empty lists to indicate failure

async def handle_attachment(attachment):
    try:
        file_extension = attachment.filename.split(".")[-1]
        unique_file_name = generate_unique_file_name(file_extension)
        file_name = f"./temp/{unique_file_name}"
        
        await attachment.save(file_name)
        logging.info(f"Saved {attachment.content_type.split('/')[0]} {file_name}")
        
        file_names = []
        uploaded_files = []
        
        file_names.append(file_name)
        uploaded_file = await asyncio.to_thread(genai.upload_file, file_name)
        uploaded_files.append(uploaded_file)
        
        logging.info(f"Uploaded {uploaded_file.display_name} as {uploaded_file.name}")
        
        return file_names, uploaded_files
    except Exception as e:
        logging.error(f"Error in handleAttachment: {e}")
        return [], [] # Return empty lists to indicate failure