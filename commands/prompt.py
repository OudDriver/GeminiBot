import ssl
import json
import datetime
import traceback
from discord.ext import commands
from google.genai.types import GenerateContentConfig, SafetySetting
from google.genai import Client

from packages.utils import *
from packages.youtube import *
from packages.tex import *
from packages.uwu import Uwuifier



CONFIG = json.load(open("config.json"))

YOUTUBE_PATTERN = re.compile(
    r'https://(www\.youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(?:\S*[&?]list=[^&]+)?(?:&index=\d+)?')
MAX_MESSAGE_LENGTH = 2000
SAFETY_SETTING = CONFIG["HarmBlockThreshold"]

thought = ""
secrets = ""
output = ""
ctxGlob = None
memory = None


def prompt(tools: list , genai_client: Client):
    @commands.hybrid_command(name="prompt")
    async def command(ctx: commands.Context, *, message: str):
        """
        Generates a response. Supports file inputs and YouTube links.

        Args:
            ctx: The context of the command invocation
            message: The message to send the bot
        """
        global ctxGlob, thought, output, memory, secrets
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
                SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold=SAFETY_SETTING),
                SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold=SAFETY_SETTING)
            ]

            config = GenerateContentConfig(system_instruction=configs['system_prompt'], tools=tools, safety_settings=safety_settings)

            # Start a new chat or resume from existing memory
            chat = genai_client.chats.create(history=memory, model=model, config=config) if memory else genai_client.chats.create(model=model, config=config)
            ctxGlob = ctx

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
                    file_names_from_func, uploaded_files_from_func = await handle_youtube(link)

                    file_names.extend(file_names_from_func)
                    uploaded_files.extend(uploaded_files_from_func)

                tasks = [handle_attachment(attachment) for attachment in ctx.message.attachments if not tools == "google_search_retrieval"]
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
                    final_prompt.insert(0,
                                        f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id} Replied To \"{replied.content}\": ")
                else:
                    final_prompt.insert(0,
                                        f"{ctx.author.name} With Display Name {ctx.author.global_name} and ID {ctx.author.id}: ")

                if tools == "google_search_retrieval":
                    final_prompt = final_prompt[0] + final_prompt[1]

                logging.info(f"Got Final Prompt {final_prompt}")

                response = chat.send_message(final_prompt)

                func_call_result = {}
                function_call = False


                # Loops until there is no more function calling left.
                while True:
                    if isinstance(tools, str):
                        break

                    # Manual function calling system
                    for part in response.candidates[0].content.parts:
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
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(name=fn, response={"result": val})) for
                            fn, val in func_call_result.items()
                        ]
                        response = chat.send_message(response_parts)
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

        except genai.types.StopCandidateException as e:
            await send_long_message(ctx, f"{e}\nThat means your prompt isn't safe! Try again!", MAX_MESSAGE_LENGTH)

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
