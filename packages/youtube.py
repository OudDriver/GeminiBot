from pytube import YouTube
import subprocess
import asyncio, re
import google.generativeai as genai

from packages.utils import generateUniqueFileName

def combineVideoAudio(videoPath: str, audioPath: str, outputPath: str):
    """
    Combines video and audio files using ffmpeg.
    """
    cmd = [
        "ffmpeg",
        "-i", videoPath,
        "-i", audioPath,
        "-c:v", "copy",  # Copy video codec
        "-c:a", "aac",   # Re-encode audio to AAC for better compatibility
        "-map", "0:v:0", # Map video stream from the first input (video file)
        "-map", "1:a:0", # Map audio stream from the second input (audio file)
        "-shortest",     # Finish encoding when the shortest input ends
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
    """a
    Checks if the uploaded file is active on Google servers.
    """
    status = genai.get_file(uploadedFile.name).state
    return status == 2

async def waitForFileActive(uploadedFile):
    """
    Waits until the uploaded file becomes active on Google servers.
    """
    while not checkFileActive(uploadedFile):
        await asyncio.sleep(1)  # Wait for 1 second before checking again