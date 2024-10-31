import ssl
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

YOUTUBE_PATTERN = re.compile(r"https://(www\.youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(?:\S*[&?]list=[^&]+)?(?:&index=\d+)?")
MAX_MESSAGE_LENGTH = 2000
SAFETY_SETTING = HARM_BLOCK_THRESHOLD[CONFIG["HarmBlockThreshold"]]
SAFETY = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: SAFETY_SETTING,
    HarmCategory.HARM_CATEGORY_HARASSMENT: SAFETY_SETTING,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: SAFETY_SETTING,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: SAFETY_SETTING
}

thought = ""
secrets = ""
output = ""
ctxGlob = None
memory = None

def prompt(tools: list):
    @commands.hybrid_command(name="prompt")
    async def command(ctx: commands.Context, *, message: str):
        global ctxGlob, thought, output, memory, secrets
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
                final_prompt = [YOUTUBE_PATTERN.sub("", message)]
                file_names = []
                uploaded_files = []

                link = YOUTUBE_PATTERN.search(message)

                # Download the files and upload them
                if link:
                    logging.info(f"Found Link {link}")
                    file_names_from_func, uploaded_files_from_func = await handle_youtube(link)
                    
                    file_names.extend(file_names_from_func)
                    uploaded_files.extend(uploaded_files_from_func)
                    
                tasks = [handle_attachment(attachment) for attachment in ctx.message.attachments]
                results = await asyncio.gather(*tasks)
                
                for result in results:
                    file_names.extend(result[0])
                    uploaded_files.extend(result[1])

                # Waits until the file is active
                if uploaded_files:
                    for uploadedFile in uploaded_files:
                        await wait_for_file_active(uploadedFile)
                        logging.info(f"{genai.get_file(uploadedFile.name).display_name} is active at server")
                        final_prompt.append(uploadedFile)

                # Added context, such as the reply and the  user
                if ctx.message.reference:
                    replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    final_prompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id} Replied To \"{replied.content}\": ")
                else:
                    final_prompt.insert(0, f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id}: ")
                    
                logging.info(f"Got Final Prompt {final_prompt}")
                
                response = await chat.send_message_async(final_prompt, safety_settings=SAFETY)
                
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
                            
                    if function_call:
                        # Adds the function calling output
                        # noinspection PyTypeChecker
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
                
                text, thought_matches, secret_matches = clean_text(text)
                thought = ""
                secrets = ""
                if thought_matches:
                    for thought_match in thought_matches:
                        thought += f"{thought_match}\n"
                    text += "(This reply have a thought)"
                if secret_matches:
                    for secret_match in secret_matches:
                        secrets += f"{secret_match}\n"
                
                await send_long_message(ctx, text, MAX_MESSAGE_LENGTH)
        
        except ssl.SSLEOFError as e:
            error_message = f"`{e}`\nPerhaps, you can try your request again!"
            logging.exception(f"Error: {error_message}")
            await send_long_message(ctx, error_message, MAX_MESSAGE_LENGTH)
        
        except genai.types.StopCandidateException as e:
            await send_long_message(ctx, f"{e}\nThat means your prompt isn't safe! Try again!", MAX_MESSAGE_LENGTH)
            
        except Exception as e:
            await send_long_message(ctx, f"`{e}`", MAX_MESSAGE_LENGTH)
            logging.exception(f"\n{e}")

        finally:
            for file in file_names:
                os.remove(file)
                logging.info(f"Deleted {os.path.basename(file)} at local server")

    return command