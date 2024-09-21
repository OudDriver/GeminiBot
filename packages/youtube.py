from pytubefix import YouTube
import subprocess
import asyncio, re
import google.generativeai as genai
import logging
import os
import time

from packages.utils import generateUniqueFileName

def downloadVideoAudio(link: str) -> tuple:
    """
    Downloads separate video and audio streams from a YouTube link and returns their paths.
    """
    video = YouTube(link).streams.first().download(output_path='./temp', filename=generateUniqueFileName('mp4')) 

    return video

def searchRegex(pattern: str, text: str):
    """
    Searches for a regex pattern in a text and returns the match if found.
    """
    match = re.search(pattern, text)
    if match:
        link = match.group(0)
        return link
    return None

def checkFileActive(uploadedFile):
    """
    Checks if the uploaded file is active on Google servers.
    """
    status = genai.get_file(uploadedFile.name).state
    return status == 2

async def waitForFileActive(uploadedFile):
    """
    Waits until the uploaded file becomes active on Google servers.
    """
    start_time = time.monotonic()
    timeout = 30

    try:
        while not checkFileActive(uploadedFile):
            if time.monotonic() - start_time >= timeout:
                logging.warning(f"Timeout while waiting for file {uploadedFile.name} to become active. Skipping Check")
                return 

            await asyncio.sleep(1)  
                
    except Exception as e:
        logging.error(f"Error while waiting for file active! {e}.")
        
async def handleYoutube(link):
    try:
        videoFile = await asyncio.to_thread(downloadVideoAudio, link.group(0))
        
        logging.info(f"Downloaded The Video {os.path.basename(videoFile)}")
        
        fileNames = []
        uploadedFiles = []
        
        fileNames.extend([videoFile])
        uploadedYoutubeFile = await asyncio.to_thread(genai.upload_file, videoFile)
        uploadedFiles.append(uploadedYoutubeFile)
        
        logging.info(f"Uploaded {uploadedYoutubeFile.display_name} as {uploadedYoutubeFile.name}")
        
        return fileNames, uploadedFiles
    except Exception as e:
        logging.exception(f"Error in handleYoutube: {e}")
        return [], [] # Return empty lists to indicate failure

async def handleAttachment(attachment):
    try:
        file_extension = attachment.filename.split(".")[-1]
        unique_file_name = generateUniqueFileName(file_extension)
        fileName = f"./temp/{unique_file_name}"
        
        await attachment.save(fileName)
        logging.info(f"Saved {attachment.content_type.split('/')[0]} {fileName}")
        
        fileNames = []
        uploadedFiles = []
        
        fileNames.append(fileName)
        uploadedFile = await asyncio.to_thread(genai.upload_file, fileName)
        uploadedFiles.append(uploadedFile)
        
        logging.info(f"Uploaded {uploadedFile.display_name} as {uploadedFile.name}")
        
        return fileNames, uploadedFiles
    except Exception as e:
        logging.exception(f"Error in handleAttachment: {e}")
        return [], [] # Return empty lists to indicate failure