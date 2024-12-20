import ssl
import json
import datetime
import traceback
import os
import re
import asyncio
import logging
import discord
from discord.ext import commands
from google.genai.types import GenerateContentConfig, SafetySetting, Part, FunctionResponse, AutomaticFunctionCallingConfig
from google.genai import Client

from packages.utils import clean_text, create_grounding_markdown, send_long_messages, send_long_message, format_args
from packages.youtube import handle_youtube
from packages.tex import render_latex, split_tex, check_tex
from packages.uwu import Uwuifier
from packages.file_utils import handle_attachment, wait_for_file_active
from packages.memory_save import load_memory

CONFIG = json.load(open("config.json"))

YOUTUBE_PATTERN = re.compile(
    r'https://(www\.youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(?:\S*[&?]list=[^&]+)?(?:&index=\d+)?')
MAX_MESSAGE_LENGTH = 2000
SAFETY_SETTING = CONFIG["HarmBlockThreshold"]

thought = ""
secrets = ""
output = ""
ctx_glob = None
memory = None

BLOCKED_SETTINGS = {
    "BLOCK_LOW_AND_ABOVE": ['LOW', 'MEDIUM', 'HIGH'],
    'BLOCK_MEDIUM_AND_ABOVE': ['MEDIUM', 'HIGH'],
    'BLOCK_ONLY_HIGH': ['HIGH']
}

def prompt(tools: list , genai_client: Client):
    @commands.hybrid_command(name="prompt")
    async def command(ctx: commands.Context, *, message: str):
        """
        Generates a response. Supports file inputs and YouTube links.

        Args:
            ctx: The context of the command invocation
            message: The message to send the bot
        """
        global ctx_glob, thought, output, memory, secrets
        try:
            # Load configuration from temporary JSON file
            with open("temp/temp_config.json", "r") as TEMP_CONFIG:
                configs = json.load(TEMP_CONFIG)


            # Initialize model and configs
            model = configs['model']
            safety_settings = [
                SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold=SAFETY_SETTING),
                SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold=SAFETY_SETTING),
                SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold=SAFETY_SETTING),
                SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold=SAFETY_SETTING),
                SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold=SAFETY_SETTING)
            ]

            config = GenerateContentConfig(system_instruction=configs['system_prompt'], tools=tools, safety_settings=safety_settings, automatic_function_calling=AutomaticFunctionCallingConfig(disable=True, maximum_remote_calls=0))

            # Start a new chat or resume from existing memory
            chat = genai_client.aio.chats.create(history=memory, model=model, config=config) if memory else genai_client.aio.chats.create(model=model, config=config)
            ctx_glob = ctx
            
            async with ctx.typing():
                # Clear context if message is {clear}
                if message.lower() == "{clear}":
                    if ctx.author.guild_permissions.administrator:
                        memory = []
                        await ctx.reply("Alright, I have cleared my context. What are we gonna talk about?")
                        logging.info("Cleared Context")
                        return
                    else:
                        await ctx.reply("You don't have the necessary permissions for this!", ephemeral=True)
                        return

                # Check for bad words and handle accordingly
                for word in CONFIG["BadWords"]:
                    if word in ctx.message.content.lower():
                        await ctx.message.delete()
                        await ctx.author.timeout(datetime.timedelta(minutes=10),
                                                 reason="Saying a word blocked in the config file")
                        await ctx.send(f"Chill <@{ctx.author.id}>! Don't say things like that.")
                        return

                logging.info(f"Received Input With Prompt: {message}")

                # Preprocessing and handling attachments/links
                final_prompt = [YOUTUBE_PATTERN.sub("", message)]
                file_names = []
                uploaded_files = []

                link = YOUTUBE_PATTERN.search(message)

                # Download the files and upload them
                if link and not tools == "google_search_retrieval":
                    logging.info(f"Found Link {link}")
                    file_names_from_func, uploaded_files_from_func = await handle_youtube(link, genai_client)

                    file_names.extend(file_names_from_func)
                    uploaded_files.extend(uploaded_files_from_func)

                tasks = [handle_attachment(attachment, genai_client) for attachment in ctx.message.attachments if not tools == "google_search_retrieval"]
                results = await asyncio.gather(*tasks)

                for result in results:
                    file_names.extend(result[0])
                    uploaded_files.extend(result[1])

                # Waits until the file is active
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        await wait_for_file_active(uploaded_file)
                        logging.info(f"{uploaded_file.name} is active at server")
                        final_prompt.append(Part.from_uri(uploaded_file.uri, uploaded_file.mime_type))

                # Added context, such as the reply and the  user
                if ctx.message.reference:
                    replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    final_prompt.insert(0,
                                        f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id} Replied To \"{replied.content}\": ")
                else:
                    final_prompt.insert(0,
                                        f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id}: ")

                if not memory:
                    mem = load_memory()
                    if mem:
                        final_prompt.insert(0, f"This is the memory you saved: {mem}")

                logging.info(f"Got Final Prompt {final_prompt}")

                response = await chat.send_message(final_prompt)

                if response.candidates[0].finish_reason == "SAFETY":
                    blocked_category = []
                    for safety in response.candidates[0].safety_ratings:
                        if safety.probability in BLOCKED_SETTINGS[SAFETY_SETTING]:
                            blocked_category.append(safety.category)

                    # noinspection PyTypeChecker
                    await ctx.reply(f"This response was blocked due to safety concerns, {''.join(blocked_category)}", ephemeral=True)
                    logging.warning(f"Response blocked due to safety: {response.candidates[0].safety_ratings}")
                    return

                func_call_result = {}
                function_call = False

                # Loops until there is no more function calling left.
                while True:
                    # Manual function calling system
                    for part in response.candidates[0].content.parts:
                        if fn := part.function_call:
                            function_call = True

                            args = format_args(fn.args)

                            # Joins the arguments
                            arg_output = ", ".join(f"{key}={val}" for key, val in args.items())
                            logging.info(f"{fn.name}({arg_output})")

                            # Finds the function
                            func = None
                            for f in tools:
                                if f.__name__ == fn.name:
                                    func = f
                                    break

                            # Calls the function
                            result = func(**args)
                            func_call_result[fn.name] = result

                    if function_call:
                        # Adds the function calling output
                        # noinspection PyTypeChecker
                        response_parts = [
                            Part(
                                function_response=FunctionResponse(name=fn, response={"result": val})) for
                            fn, val in func_call_result.items()
                        ]
                        response = await chat.send_message(response_parts)
                        function_call = False

                    else:
                        break

                text = response.text
                logging.info(f"Got Response.\n{text}")

                memory = chat._curated_history

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
                if tools == "google_search_retrieval":
                    text = "### Multi-modality not supported while using the Google Search Retrieval tool.\n" + text + f"\n{create_grounding_markdown(response.candidates)}"

                if configs['uwu']:
                    uwu = Uwuifier()
                    text = uwu.uwuify_sentence(text)

                response_if_tex = split_tex(text)

                if len(response_if_tex) > 1:
                    for i, tex in enumerate(response_if_tex):
                        if check_tex(tex):
                            logging.info(tex)
                            file = render_latex(tex)
                            file_names.append(file)
                            response_if_tex[i] = discord.File(file)
                    await send_long_messages(ctx, response_if_tex, MAX_MESSAGE_LENGTH)
                else:
                    await send_long_message(ctx, text, MAX_MESSAGE_LENGTH)

        except ssl.SSLEOFError as e:
            error_message = f"`{e}`\nPerhaps, you can try your request again!"
            logging.error(f"Error: {error_message}")
            await send_long_message(ctx, error_message, MAX_MESSAGE_LENGTH)

        except Exception as e:
            await send_long_message(ctx, f"`{e}`", MAX_MESSAGE_LENGTH)
            logging.error(traceback.format_exc())

        finally:
            try:
                for file in file_names:
                    os.remove(file)
                    logging.info(f"Deleted {os.path.basename(file)} at local server")
            except UnboundLocalError:
                pass

    return command
