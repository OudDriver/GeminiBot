from pytubefix import YouTube
import subprocess
import asyncio, re
import google.generativeai as genai
import logging
import os

from packages.utils import generateUniqueFileName

def combineVideoAudio(videoPath: str, audioPath: str, outputPath: str):
    """
    Combines video and audio files using ffmpeg.
    """
    cmd = [
        "ffmpeg",
        "-i", videoPath,
        "-i", audioPath,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        outputPath
    ]
    subprocess.run(cmd)

def downloadVideoAudio(link: str):
    """
    Downloads separate video and audio streams from a YouTube link and returns their paths.
    """
    video = YouTube(link).streams.filter(adaptive=True).first().download(output_path='./temp', filename=generateUniqueFileName('mp4')) 
    audio = YouTube(link).streams.filter(only_audio=True).first().download(output_path='./temp', filename=generateUniqueFileName('mp3'))

    return (video, audio)

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
    try:
        async with asyncio.timeout(10): 
            while not checkFileActive(uploadedFile):
                await asyncio.sleep(1)  # Wait for 1 second before checking again
                
    except asyncio.TimeoutError:
        logging.warning(f"Timeout while waiting for file {uploadedFile.name} to become active. Skipping Check")
        
    except Exception as e:
        logging.error(f"Error while waiting for file active! {e}.")
        
async def handleYoutube(link):
    try:
        output = f'./temp/{generateUniqueFileName("mp4")}'
        videoFile, audioFile = await asyncio.to_thread(downloadVideoAudio, link.group(0))
        
        logging.info(f"Downloaded The Video {os.path.basename(videoFile)} and The Audio {os.path.basename(audioFile)}")
        
        await asyncio.to_thread(combineVideoAudio, videoFile, audioFile, output)
        logging.info(f"Combined {os.path.basename(videoFile)} and {os.path.basename(audioFile)} to Make {os.path.basename(output)}")
        
        fileNames = []
        uploadedFiles = []
        
        fileNames.extend([videoFile, audioFile, output])
        uploadedYoutubeFile = await asyncio.to_thread(genai.upload_file, output)
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