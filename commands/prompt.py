from anyio import fail_after
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

thought = ""
memory = None

def prompt(tools: list):
    @commands.hybrid_command(name="prompt")
    async def command(ctx: commands.Context, *, message: str):
        global ctxGlob, thought, output, memory
        """
        Generates text based on a given message and optional image, video, audio attachments. Also supports YouTube link.
        """
        try:
            # Load configuration from temporary JSON file
            with open("temp/workaround.json", "r") as TEMP_CONFIG:
                configs = json.load(TEMP_CONFIG)

            # Initialize the GenAI model with configuration and safety settings
            model = genai.GenerativeModel(configs['model'], SAFETY_SETTING, system_instruction=configs['system_prompt'], tools=tools)

            # Start a new chat or resume from existing memory
            chat = model.start_chat(history=memory) if memory else model.start_chat()
            ctxGlob = ctx
            async with ctx.typing():
                # Clear context if message is {clear}
                if message.lower() == "{clear}":
                    memory = []
                    await ctx.reply("Alright, I have cleared my context. What are we gonna talk about?")
                    return
                
                # Check for bad words and handle accordingly
                for word in CONFIG["BadWords"]:
                    if word in ctx.message.content.lower():
                        await ctx.message.delete()
                        await ctx.author.timeout(datetime.timedelta(minutes=10), reason="Saying a word blocked in config.json")
                        await ctx.send(f"Chill <@{ctx.author.id}>! Don't say things like that.")
                        return
                
                logging.info(f"Received Input With Prompt: {message}")
                
                # Preprocessing and handling attachments/links
                finalPrompt = [YOUTUBE_PATTERN.sub("", message)]
                fileNames = []
                uploadedFiles = []

                link = YOUTUBE_PATTERN.search(message)

                # Download the files and upload them
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

                # Waits until the file is active
                if uploadedFiles:
                    for uploadedFile in uploadedFiles:
                        await waitForFileActive(uploadedFile)
                        logging.info(f"{genai.get_file(uploadedFile.name).display_name} is active at server")
                        finalPrompt.append(uploadedFile)

                # Added context, such as the reply and the  user
                if ctx.message.reference:
                    reply = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    finalPrompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id} Replied To \"{reply.content}\": ")
                else:
                    finalPrompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id}: ")
                    
                logging.info(f"Got Final Prompt {finalPrompt}")
                
                response = await chat.send_message_async(finalPrompt, safety_settings=SAFETY)
                
                func_call_result = {}
                function_call = False
                    
                # Loops until there is no more function calling left.
                while True:
                    # Manual function calling system
                    for part in response.parts:
                        if fn := part.function_call:
                            function_call = True
                            
                            # Joins the arguments
                            arg_output = ", ".join(f"{key}={val}" for key, val in fn.args.items())
                            logging.info(f"{fn.name}({arg_output})")
                            
                            # Finds the function
                            func = None
                            for f in tools:
                                if f.__name__ == fn.name:
                                    func = f
                                    break
                            
                            args = fn.args
                            
                            # Calls the function
                            result = func(**args)
                            func_call_result[fn.name] = result
                            
                    if function_call == True:
                        # Adds the function calling output
                        response_parts = [
                            genai.protos.Part(function_response=genai.protos.FunctionResponse(name=fn, response={"result": val})) for fn, val in func_call_result.items()
                        ]
                        response = await chat.send_message_async(response_parts, safety_settings=SAFETY)
                        function_call = False
                        
                    else:
                        break
                
                
                    
                text = response.text
                logging.info(f"Got Response.\n{text}")
                
                memory = chat.history 
                
                text, matches = clean_text(text)
                thought = ""
                if matches:
                    for match in matches:
                        thought += f"{match}\n"
                    text += "(This reply have a thought)"
                
                await sendLongMessage(ctx, text, MAX_MESSAGE_LENGTH)
        
        except ssl.SSLEOFError as e:
            errorMessage = f"`{e}`\nPerhaps, you can try your request again!"
            logging.exception(f"Error: {errorMessage}")
            await sendLongMessage(ctx, errorMessage, MAX_MESSAGE_LENGTH)
        
        except genai.types.StopCandidateException as e:
            await sendLongMessage(ctx, f"{e}\nThat means your prompt isn't safe! Try again!", MAX_MESSAGE_LENGTH)
            
        except Exception as e:
            await sendLongMessage(ctx, f"`{e}`", MAX_MESSAGE_LENGTH)
            logging.exception(f"\n{e}")

        finally:
            try:
                for file in fileNames:
                    os.remove(file)
                    logging.info(f"Deleted {os.path.basename(file)} at local server")
            except Exception as e:
                pass

    return command