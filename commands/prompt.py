import google.generativeai as genai
import logging
import re
import traceback
import ssl
import asyncio
import json
import datetime

from discord.ext import commands
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from packages.utils import *
from packages.youtube import *

HARM_BLOCK_THRESHOLD = {
    "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
}

CONFIG = json.load(open("config.json"))

YOUTUBE_PATTERN = re.compile(r"https://(www\.youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(?:\S*(?:&|\?)list=[^&]+)?(?:&index=\d+)?")
MAX_MESSAGE_LENGTH = 2000
SAFETY_SETTING = HARM_BLOCK_THRESHOLD[CONFIG["HarmBlockThreshold"]]
SAFETY = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: SAFETY_SETTING,
    HarmCategory.HARM_CATEGORY_HARASSMENT: SAFETY_SETTING,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: SAFETY_SETTING,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: SAFETY_SETTING
}

def prompt(model: genai.GenerativeModel):
    chat = model.start_chat(enable_automatic_function_calling=True)
    @commands.command(name="prompt")
    async def command(ctx: commands.Context, *, message: str):
        """
        Generates text based on a given message and optional image, video, audio attachments. Also supports YouTube link.
        """
        try:
            async with ctx.typing():
                if message.lower() == "{clear}":
                    for _ in range(len(chat.history) // 2):
                        chat.rewind()
                        
                    print(chat.history)
                    await ctx.reply("Alright, I have cleared my context. What are we gonna talk about?")
                    return
                
                for word in CONFIG["BadWords"]:
                    if word in ctx.message.content.lower():
                        await ctx.message.delete()
                        await ctx.author.timeout(datetime.timedelta(minutes=10), reason="Saying a word blocked in config.json")
                        await ctx.send(f"Chill <@{ctx.author.id}>! Don't be racist like that.")
                        return
                
                logging.info(f"Received Input With Prompt: {message}")
                
                finalPrompt = [YOUTUBE_PATTERN.sub("", message)]
                fileNames = []
                uploadedFiles = []

                link = YOUTUBE_PATTERN.search(message)

                if link:
                    logging.info(f"Found Link {link}")
                    fileNamesFromFunc, uploadedFilesFromFunc = await handleYoutube(link)
                    
                    fileNames.extend(fileNamesFromFunc)
                    uploadedFiles.extend(uploadedFilesFromFunc)
                    
                tasks = [handleAttachment(attachment) for attachment in ctx.message.attachments]
                results = await asyncio.gather(*tasks)
                
                for result in results:
                    fileNames.extend(result[0])
                    uploadedFiles.extend(result[1])

                if uploadedFiles:
                    for uploadedFile in uploadedFiles:
                        await waitForFileActive(uploadedFile)
                        logging.info(f"{genai.get_file(uploadedFile.name).display_name} is active at server")
                        finalPrompt.append(uploadedFile)

                if ctx.message.reference:
                    reply = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    finalPrompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id} Replied To \"{reply.content}\": ")
                else:
                    finalPrompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id}: ")
                    
                logging.info(f"Got Final Prompt {finalPrompt}")
                
                response = await chat.send_message_async(finalPrompt, safety_settings=SAFETY)
                text = response.text
                logging.info(f"Got Response.\n{text}")
                
                await sendLongMessage(ctx, text, MAX_MESSAGE_LENGTH)
        
        except ssl.SSLEOFError as e:
            errorMessage = f"`{e}`\nPerhaps, you can try your request again!"
            logging.exception(f"Error: {errorMessage}")
            await sendLongMessage(ctx, errorMessage, MAX_MESSAGE_LENGTH)
        
        except genai.types.StopCandidateException as e:
            await sendLongMessage(ctx, f"Your prompt is not safe! Try again with a safer prompt.", MAX_MESSAGE_LENGTH)
            
        except Exception as e:
            errorMessage = traceback.format_exc()
            logging.exception(f"Error: {errorMessage}")
            await sendLongMessage(ctx, f"`{traceback.format_exception_only(e)[0]}`", MAX_MESSAGE_LENGTH)

        finally:
            """
            try:
                for file in fileNames:
                    os.remove(file)
                    logging.info(f"Deleted {os.path.basename(file)} at local server")
                for uploadedFile in uploadedFiles:
                    logging.info(f"Deleted {uploadedFile.name} at Google server")
                    await asyncio.to_thread(genai.delete_file, uploadedFile.name)
            except Exception as e:
                pass
            """

    return command