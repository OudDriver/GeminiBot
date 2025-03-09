from pytubefix import YouTube
from google import genai
import asyncio, re
import logging
import os

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
        
async def handle_youtube(link, client: genai.Client):
    try:
        video_file = await asyncio.to_thread(download_video, link.group(0))
        
        logging.info(f"Downloaded The Video {os.path.basename(video_file)}")
        
        file_names = []
        uploaded_files = []
        
        file_names.extend([video_file])
        uploaded_youtube_file = await asyncio.to_thread(client.files.upload, file=video_file)
        uploaded_files.append(uploaded_youtube_file)
        
        logging.info(f"Uploaded {uploaded_youtube_file.display_name} as {uploaded_youtube_file.name}")
        
        return file_names, uploaded_files
    except Exception as e:
        logging.error(f"Error in handleYoutube: {e}")
        return [], [] # Return empty lists to indicate failure

