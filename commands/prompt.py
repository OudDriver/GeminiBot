import ssl
import json
from datetime import datetime, timezone
import traceback
import os
import regex
import asyncio
import logging
import discord
from discord.ext import commands
from google.genai.types import GenerateContentConfig, SafetySetting, Part,\
    AutomaticFunctionCallingConfig, HarmCategory, FinishReason, FileData
from google.genai import Client

from packages.utils import clean_text, create_grounding_markdown, send_long_messages, \
    send_long_message, send_image, generate_unique_file_name, repair_links
from packages.tex import render_latex, split_tex, check_tex
from packages.uwu import Uwuifier
from packages.file_utils import handle_attachment, wait_for_file_active
from packages.memory_save import load_memory
from packages.maps import BLOCKED_CATEGORY, HARM_PRETTY_NAME

CONFIG = json.load(open("config.json"))

YOUTUBE_PATTERN = regex.compile(r'(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)('
                                r'?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9\_-]+)')
MAX_MESSAGE_LENGTH = 2000
SAFETY_SETTING = CONFIG["HarmBlockThreshold"]

latest_token_count = 0
thought = ""
secrets = ""
ctx_glob = None
memory = []

def prompt(tools: list , genai_client: Client):
    async def command(ctx: commands.Context): 
        """
        Generates a response. Supports file inputs and YouTube links.

        Args:
            ctx: The context of the command invocation
        """
        global ctx_glob, thought, memory, secrets, latest_token_count
        try:
            is_reply_to_bot = False
            if ctx.message.reference:
                try:
                    replied_message = await ctx.fetch_message(ctx.message.reference.message_id)
                    is_reply_to_bot = replied_message.author.id == ctx.bot.user.id
                except discord.NotFound:
                    logging.warning(f"Referenced message not found (ID: {ctx.message.reference.message_id}).")
                except discord.HTTPException as e:
                    logging.error(f"HTTP Error fetching referenced message: {e}")
                    await ctx.send(f"Error fetching referenced message: {e}")
                    return

            is_mention = ctx.message.mentions and ctx.bot.user in ctx.message.mentions

            if not (is_reply_to_bot or is_mention):
                return

            message = ctx.message.content.replace(f'<@{ctx.bot.user.id}>', '').strip()
            if not message:
                return await ctx.send("You mentioned me or replied to me, but you didn't give me any prompt!")

            now = datetime.now(timezone.utc)
            formatted_time = now.strftime("%A, %B %d, %Y %H:%M:%S UTC")
            
            with open("temp/temp_config.json", "r") as TEMP_CONFIG:
                configs = json.load(TEMP_CONFIG)
            
            model = configs['model']
            safety_settings = [
                SafetySetting(category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=SAFETY_SETTING),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=SAFETY_SETTING),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=SAFETY_SETTING),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=SAFETY_SETTING),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=SAFETY_SETTING)
            ]

            config = GenerateContentConfig(
                system_instruction=configs['system_prompt'],
                tools=tools,
                safety_settings=safety_settings,
                automatic_function_calling=AutomaticFunctionCallingConfig(maximum_remote_calls=5)
            )

            async with ((ctx.typing())):
                if message.lower() == "{clear}":
                    if ctx.author.guild_permissions.administrator:
                        memory.clear()
                        await ctx.reply("Alright, I have cleared my context. What are we gonna talk about?")
                        logging.info("Cleared Context")
                        return
                    else:
                        await ctx.reply("You don't have the necessary permissions for this!", ephemeral=True)
                        return
                
                if memory:
                    chat = genai_client.aio.chats.create(
                        history=memory, model=model, config=config
                    )
                else:
                    chat = genai_client.aio.chats.create(model=model, config=config)

                ctx_glob = ctx
                logging.info(f"Received Input With Prompt: {message}")
                
                final_prompt = [YOUTUBE_PATTERN.sub("", message)]
                file_names = []
                uploaded_files = []

                tasks = [handle_attachment(attachment, genai_client) for attachment in ctx.message.attachments]
                results = await asyncio.gather(*tasks)

                if ctx.message.attachments and not hasattr(results[0], "__getitem__"):
                    await send_long_message(
                        ctx,
                        f"Error: Failed to upload attachment(s). Continuing as if the files are not uploaded. `{results[0]}`",
                        MAX_MESSAGE_LENGTH
                    )
                else:
                    for result in results:
                        file_names.extend(result[0])
                        uploaded_files.extend(result[1])

                
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        await wait_for_file_active(uploaded_file)
                        logging.info(f"{uploaded_file.name} is active at server")
                        final_prompt.append(Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type))

                
                if ctx.message.reference:
                    replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    final_prompt.insert(0,
                                        (f"{formatted_time}, {ctx.author.name} With Display Name "
                                         f"{ctx.author.display_name} and ID {ctx.author.id} Replied to your message, \"{replied.content}\": "))
                else:
                    final_prompt.insert(0,
                                        f"{formatted_time}, {ctx.author.name} With Display Name {ctx.author.display_name} and ID {ctx.author.id}: ")

                if not memory:
                    mem = load_memory()
                    if mem:
                        final_prompt.insert(0, f"This is the memory you saved: {mem}")

                links = regex.finditer(YOUTUBE_PATTERN, message)
                
                if links:
                    for link in links:
                        for i, final in enumerate(final_prompt):
                            final_prompt[i] = regex.sub(YOUTUBE_PATTERN, "", final)
                        url = repair_links(link.group())
                        file = FileData(file_uri=url)
                        logging.info(f"Found and Processed Link {url}")
                        final_prompt.append(Part(file_data=file))

                logging.info(f"Got Final Prompt {final_prompt}")

                response = await chat.send_message(final_prompt)

                if response.candidates[0].finish_reason == FinishReason.SAFETY:
                    blocked_category = []
                    for safety in response.candidates[0].safety_ratings:
                        if safety.probability in BLOCKED_CATEGORY[SAFETY_SETTING]:
                            blocked_category.append(HARM_PRETTY_NAME[safety.category.name])

                    await ctx.reply(f"This response was blocked due to {', '.join(blocked_category)}", ephemeral=True)
                    logging.warning(f"Response blocked due to safety: {blocked_category}")
                    return


                latest_token_count = response.usage_metadata.total_token_count

                contains_code_exec = False
                for part in response.candidates[0].content.parts:
                    if part.executable_code is not None or part.code_execution_result is not None or part.inline_data is not None:
                        contains_code_exec = True
                        break

                memory = chat._curated_history

                async def handle_text_only_messages():
                    global thought, secrets
                    text, thought_matches, secret_matches = clean_text(part.text)
                    thought = ""
                    secrets = ""
                    if thought_matches:
                        for thought_match in thought_matches:
                            thought += f"{thought_match}\n"
                        text += "\n(This reply have a thought)"

                    if secret_matches:
                        for secret_match in secret_matches:
                            secrets += f"{secret_match}\n"

                    if tools == "google_search_retrieval":
                        text = text + f"\n{create_grounding_markdown(response.candidates)}"

                    if configs['uwu']:
                        uwu = Uwuifier()
                        text = uwu.uwuify_sentence(text)

                    if response.candidates[0].finish_reason == FinishReason.MAX_TOKENS:
                        text = text + "\n(Response May Be Cut Off)"

                    response_if_tex = split_tex(text)

                    if len(response_if_tex) > 1:
                        for j, tex in enumerate(response_if_tex):
                            if check_tex(tex):
                                logging.info(tex)
                                file_tex = render_latex(tex)
                                if not file_tex:
                                    response_if_tex[j] += " (Contains Invalid LaTeX Expressions)"
                                    continue
                                file_names.append(file_tex)
                                response_if_tex[j] = discord.File(file_tex)

                        await send_long_messages(ctx, response_if_tex, MAX_MESSAGE_LENGTH)
                    else:
                        await send_long_message(ctx, text, MAX_MESSAGE_LENGTH)

                    logging.info(f"Sent\nText:\n{text}\nThought:\n{thought}\nSecrets:\n{secrets}")

                if contains_code_exec:
                    for part in response.candidates[0].content.parts:
                        logging.info(f"Got Code Execution Response.")
                        if part.text is not None:
                            await handle_text_only_messages()
                        if part.executable_code is not None:
                            logging.info("Ran Code Execution:\n" + part.executable_code.code)
                            await send_long_message(ctx,
                                                    f"Code:\n```{part.executable_code.language.name.lower()}\n{part.executable_code.code}\n```",
                                                    MAX_MESSAGE_LENGTH)
                        if part.code_execution_result is not None:
                            logging.info(f"Code Execution Output:\n{part.code_execution_result.output}")
                            await send_long_message(ctx,
                                                    f"Output:\n```\n{part.code_execution_result.output}\n```",
                                                    MAX_MESSAGE_LENGTH)
                        if part.inline_data is not None: 
                            logging.info("Got Code Execution Image")
                            file_name = './temp/' + generate_unique_file_name("png")
                            try:
                                with open(file_name, "wb") as f:
                                    f.write(part.inline_data.data)
                            except Exception as e:
                                logging.error(e)

                            file_names.append(file_name)

                            await send_image(ctx, file_name)
                else:
                    await handle_text_only_messages()

        except ssl.SSLEOFError as e:
            error_message = (f"A secure connection error occurred (SSL connection unexpectedly closed)."
                             f"This may be due to a temporary network problem or an issue with the server."
                             f"You can try again. If the problem persists, you can wait or you can contact Google. `{e}`.")
            logging.error(f"Error: {error_message}")
            await send_long_message(ctx, error_message, MAX_MESSAGE_LENGTH)

        except Exception as e:
            await send_long_message(ctx, f"A general error happened! `{e}`", MAX_MESSAGE_LENGTH)
            logging.error(traceback.format_exc())

        finally:
            try:
                for file in file_names:
                    os.remove(file)
                    logging.info(f"Deleted {os.path.basename(file)} at local server")
            except UnboundLocalError:
                pass

    return command
