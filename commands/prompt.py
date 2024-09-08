from discord.ext import commands
import google.generativeai as genai
import logging
import os
import re
import traceback
import ssl
import asyncio

from packages.utils import *
from packages.youtube import *

YOUTUBE_PATTERN = re.compile(r"https://(www\.youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(?:\S*(?:&|\?)list=[^&]+)?(?:&index=\d+)?")
MAX_MESSAGE_LENGTH = 2000
SAFETY_SETTINGS = {
    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH
}

def prompt(model: genai.GenerativeModel):
    chat = model.start_chat(enable_automatic_function_calling=True)
    @commands.command(name="prompt")
    async def command(ctx: commands.Context, *, message: str):
        """
        Generates text based on a given message and optional image, video, audio attachments. Also supports YouTube link.
        """
        try:
            logging.info(f"Received Input With Prompt: {message}")
            
            finalPrompt = [YOUTUBE_PATTERN.sub("", message)]
            fileNames = []
            uploadedFiles = []

            link = YOUTUBE_PATTERN.search(message)

            async def handleYoutube(link):
                output = f'./temp/{generateUniqueFileName("mp4")}'
                videoFile, audioFile = await asyncio.to_thread(downloadVideoAudio, link.group(0))
                
                logging.info(f"Downloaded The Video {os.path.basename(videoFile)} and The Audio {os.path.basename(audioFile)}")
                
                await asyncio.to_thread(combineVideoAudio, videoFile, audioFile, output)
                logging.info(f"Combined {os.path.basename(videoFile)} and {os.path.basename(audioFile)} to Make {os.path.basename(output)}")
                
                fileNames.extend([videoFile, audioFile, output])
                uploadedYoutubeFile = await asyncio.to_thread(genai.upload_file, output)
                uploadedFiles.append(uploadedYoutubeFile)
                
                logging.info(f"Uploaded {uploadedYoutubeFile.display_name} as {uploadedYoutubeFile.name}")

            if link:
                logging.info(f"Found Link {link}")
                await handleYoutube(link)

            async def handleAttachment(attachment):
                file_extension = attachment.filename.split(".")[-1]
                unique_file_name = generateUniqueFileName(file_extension)
                fileName = f"./temp/{unique_file_name}"

                await attachment.save(fileName)
                logging.info(f"Saved {attachment.content_type.split('/')[0]} {fileName}")
                
                fileNames.append(fileName)
                uploadedFile = await asyncio.to_thread(genai.upload_file, fileName)
                uploadedFiles.append(uploadedFile)
                
                logging.info(f"Uploaded {uploadedFile.display_name} as {uploadedFile.name}")
            

            tasks = [handleAttachment(attachment) for attachment in ctx.message.attachments]
            await asyncio.gather(*tasks)

            if uploadedFiles:
                for uploadedFile in uploadedFiles:
                    await waitForFileActive(uploadedFile)
                    logging.info(f"{genai.get_file(uploadedFile.name).display_name} is active at server")
                    finalPrompt.append(uploadedFile)

            finalPrompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id}: ")
            logging.info(f"Got Final Prompt {finalPrompt}")
            
            response = chat.send_message(finalPrompt, safety_settings=SAFETY_SETTINGS)
            logging.info(f"Got Response.\n{response}")
            text = response.text
            cleanedText = text
            
            await sendLongMessage(ctx, cleanedText, MAX_MESSAGE_LENGTH)
        
        except ssl.SSLEOFError as e:
            errorMessage = f"{e}!\nPerhaps, you can try your request again!"
            logging.exception(f"Error: {errorMessage}")
            await sendLongMessage(ctx, errorMessage, MAX_MESSAGE_LENGTH)
            
        except Exception as e:
            errorMessage = traceback.format_exc()
            if response:
                errorMessage += f"\nPerhaps this error is caused by bad safety ratings:\n{response.candidates[3]}"
            logging.exception(f"Error: {errorMessage}")
            await sendLongMessage(ctx, traceback.format_exception_only(e), MAX_MESSAGE_LENGTH)
            
        finally:
            for file in fileNames:
                os.remove(file)
                logging.info(f"Deleted {os.path.basename(file)} at local server")
            for uploadedFile in uploadedFiles:
                logging.info(f"Deleted {uploadedFile.name} at Google server")
                await asyncio.to_thread(genai.delete_file, uploadedFile.name)

    return command