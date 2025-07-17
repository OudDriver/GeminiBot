from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anyio
import discord
import regex
from google.genai.types import (
    AutomaticFunctionCallingConfig,
    Candidate,
    FileData,
    FinishReason,
    GenerateContentConfig,
    GenerateContentResponse,
    HarmBlockThreshold,
    HarmCategory,
    Part,
    PrebuiltVoiceConfig,
    SafetySetting,
    SpeechConfig,
    ThinkingConfig,
    Tool,
    VoiceConfig,
)

from packages.maps import (
    BLOCKED_CATEGORY,
    HARM_BLOCK_CATEGORY,
    HARM_PRETTY_NAME,
    MAX_MESSAGE_LENGTH,
    YOUTUBE_PATTERN,
)
from packages.utilities.errors import HandleAttachmentError
from packages.utilities.file_utils import (
    handle_attachment,
    load_config,
    read_temp_config,
    save_temp_config,
    wait_for_file_active,
)
from packages.utilities.general_utils import (
    clean_text,
    create_grounding_markdown,
    generate_unique_file_name,
    repair_links,
    send_file,
    send_long_message,
    send_long_messages,
)
from packages.utilities.tex_utilities import check_tex, render_latex, split_tex
from packages.uwu import Uwuifier

if TYPE_CHECKING:
    from discord.ext import commands
    from google.genai import Client
    from google.genai.chats import AsyncChat

logger = logging.getLogger(__name__)


def make_safety_setting(safety_setting: HarmBlockThreshold) -> list[SafetySetting]:
    """Make a safety setting template.

    Returns:
        An array of safety settings.

    """
    return [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=safety_setting,
        ),
    ]


def generate_config(
        system_instructions: str | None,
        tool_func_call: list[Tool] | None,
        safety_settings: list[SafetySetting] | None,
        auto_func_call: AutomaticFunctionCallingConfig | None,
        response_modalities: list[str],
        temperature: float | None,
) -> GenerateContentConfig:
    """Generate a config for Gemini.

    Args:
        system_instructions: the system prompt
        tool_func_call: a list of tools you want to give Gemini
        safety_settings: the safety settings you want to put
        auto_func_call: an automatic function calling config
        response_modalities: how you want Gemini to respond
        temperature: the temperature you want to give the LLM

    Returns:
        A GenerateContentConfig with system instructions, tools, safety settings,
        automatic function calling, response_modalities, temperature,
        and thinking_config.

    """
    temp_config = read_temp_config()
    return GenerateContentConfig(
        system_instruction=system_instructions,
        tools=tool_func_call,
        safety_settings=safety_settings,
        automatic_function_calling=auto_func_call,
        response_modalities=response_modalities,
        temperature=temperature,
        thinking_config=ThinkingConfig(
            include_thoughts=temp_config["thinking"],
            thinking_budget=temp_config["thinking_budget"],
        ),
    )


def has_attribute(obj: object) -> bool:
    """Check if object has an attribute.

    Returns:
        True if object has an attribute. False otherwise.

    """
    return hasattr(obj, "__getitem__")


def modify_text(
        text: str,
        candidates: list[Candidate],
        finish_reason: FinishReason,
        temp_config: dict,
        tools: list[Tool],
) -> str:
    """Modify text based off certain conditions.

    Args:
        text: the text to modify
        candidates: The candidates of the response from Gemini
        finish_reason: The finish reason of the response
        temp_config: The temp_config. Look to save_temp_config method
                     for the layout.
        tools: A list of tool.

    Returns:
        The modified text.

    """
    if temp_config["uwu"]:
        uwu = Uwuifier()
        text = uwu.uwuify_sentence(text)

    if any(not callable(tool) and tool.google_search for tool in tools):
        candidate = candidates[0]
        text += f"\n{create_grounding_markdown(candidate)}"

    if finish_reason == FinishReason.MAX_TOKENS:
        text += "\n(Response May Be Cut Off)"

    return text


def process_latex_chunk(tex_chunk: str) -> tuple[str | discord.File, str | None]:
    """Process a text chunk, attempting to render it as LaTeX if applicable.

    Args:
        tex_chunk: The string chunk to process.

    Returns:
        A tuple containing:
        - The object to be sent in the message (str or discord.File).
        - The path to the generated LaTeX file if successful, otherwise None.

    """
    if not check_tex(tex_chunk):
        return tex_chunk, None  # Not LaTeX, return as is

    logger.info(f"Attempting to render LaTeX: {tex_chunk}")
    file_path = render_latex(tex_chunk) # Assumes this returns path or None

    if file_path:
        try:
            # Successfully rendered
            logger.info(f"Rendered LaTeX successfully to: {file_path}")
            discord_file = discord.File(file_path)
            return discord_file, file_path
        except FileNotFoundError:
            logger.exception(
                f"Rendered LaTeX file not found at expected path: {file_path}",
            )
            return f"{tex_chunk} (Error: Rendered file not found)", None
        except Exception:
            logger.exception(f"Error creating discord.File for {file_path}.")
            return f"{tex_chunk} (Error preparing file for Discord)", None
    else:
        # Failed to render or deemed invalid by render_latex
        logger.warning(f"Failed to render LaTeX chunk or invalid: {tex_chunk}")
        return f"{tex_chunk} (Contains Invalid LaTeX Expressions)", None


async def handle_output(
        ctx: commands.Context,
        part: Part,
        candidates: list[Candidate],
        finish_reason: FinishReason,
        temp_config: dict[str, Any],
        tools: list[Tool],
) -> list:
    """Handle an output for Gemini and reply to Discord via the context object given.

    Args:
        ctx: The context of the command invocation
        part: A part from one of the candidates of the Gemini response
        candidates: The candidates of the response from Gemini
        finish_reason: The finish reason of the response
        temp_config: The temp_config. Look to save_temp_config method
                     for the layout.
        tools: A list of tool.

    Returns:
        A list of files processed by the function.

    """
    file_names = []
    if part.executable_code is not None:
        logger.info(f"Ran Code Execution:\n{part.executable_code.code}")

        language = part.executable_code.language.name.lower()
        code = part.executable_code.code

        await send_long_message(
            ctx,
            f"Code:\n```{language}\n{code}\n```",
            MAX_MESSAGE_LENGTH,
        )

    if part.code_execution_result is not None:
        code_exec_output = part.code_execution_result.output

        logger.info(
            f"Code Execution Output:\n{code_exec_output}",
        )
        await send_long_message(
            ctx,
            f"Output:\n```\n{part.code_execution_result.output}\n```",
            MAX_MESSAGE_LENGTH,
        )

    if part.inline_data is not None:
        logger.info("Got Image")
        file_name = "./temp/" + generate_unique_file_name("png")
        async with await anyio.open_file(file_name, "wb") as f:
            await f.write(part.inline_data.data)

        file_names.append(file_name)
        await send_file(ctx, file_name)

    if part.text is not None and not part.thought:
        text, secret_matches = clean_text(part.text)

        if secret_matches:
            save_temp_config(secret=secret_matches)

        mod_text = modify_text(text, candidates, finish_reason, temp_config, tools)
        split_parts, has_tex = split_tex(mod_text)

        if has_tex:
            message = []
            latex_files_generated = []

            for chunk in split_parts:
                processed_item, generated_file_path = process_latex_chunk(chunk)
                message.append(processed_item)
                if generated_file_path:
                    latex_files_generated.append(generated_file_path)
            await send_long_messages(ctx, message, MAX_MESSAGE_LENGTH)
            file_names.extend(latex_files_generated)

        else:
            await send_long_message(ctx, mod_text, MAX_MESSAGE_LENGTH)

        logger.info(f"Sent\nText:\n{text}")

    return file_names


def handle_whether_thought(parts: list[Part]) -> None:
    """Handles all thought part from a list of parts.

    Args:
        parts: The list of part to handle
    """
    thoughts = [part.text for part in parts if part.text is not None and part.thought]
    save_temp_config(thought=thoughts)


async def validate_invocation(ctx: commands.Context, message: str) -> bool:
    """Check if the message is a valid invocation (reply or mention with content).

    Returns:
        True if processing should stop (invalid invocation), False otherwise.

    """
    is_reply_to_bot = False
    if ctx.message.reference:
        # Fetch replied message to check author
        try:
            replied_message = await ctx.fetch_message(ctx.message.reference.message_id)
            is_reply_to_bot = replied_message.author.id == ctx.bot.user.id
        except Exception:
            # Handle potential errors fetching the replied message
            logger.exception("Failed to fetch replied message.")
            # Decide how to handle this - for now, treat as not a reply to bot
            is_reply_to_bot = False


    is_mention = ctx.message.mentions and ctx.bot.user in ctx.message.mentions

    if not (is_reply_to_bot or is_mention):
        return True  # Not a valid invocation

    if not message:
        await ctx.send(
            "You mentioned me or replied to me, "
            "but you didn't give me any prompt!",
        )
        return True  # Invalid prompt

    return False # Valid invocation, continue processing


def prepare_api_config(
        tools: list[Tool],
) -> tuple[str, GenerateContentConfig, HarmBlockThreshold, dict]:
    """Load config and prepares the API configuration object."""
    config = load_config()
    safety_setting_config = config["HarmBlockThreshold"]
    safety_setting = HARM_BLOCK_CATEGORY[safety_setting_config]
    temperature = config["Temperature"]

    temp_config = read_temp_config()
    model = temp_config["model"]
    safety_settings = make_safety_setting(safety_setting)

    if model == "gemini-2.0-flash-exp-image-generation":
        response_modalities = ["Text", "Image"]
        tool_func_call = None
        auto_func_call = None
        system_instructions = None
    else:
        response_modalities = None
        tool_func_call = tools
        auto_func_call = AutomaticFunctionCallingConfig(maximum_remote_calls=5)
        system_instructions = temp_config["system_prompt"]

    api_config = generate_config(
        system_instructions,
        tool_func_call,
        safety_settings,
        auto_func_call,
        response_modalities,
        temperature,
    )
    return model, api_config, safety_setting, temp_config


def create_chat(
        genai_client: Client,
        model: str,
        config: GenerateContentConfig,
        history: list,
) -> AsyncChat:
    """Create a chat instance with or without history."""
    if history:
        return genai_client.aio.chats.create(
            history=history,
            model=model,
            config=config,
        )
    return genai_client.aio.chats.create(model=model, config=config)


async def process_attachments(
        ctx: commands.Context,
        genai_client: Client,
        final_prompt: list,
) -> list[str]:
    """Process attachments, uploads them, and adds them to final_prompt.

    Returns:
         Local file names.

    """
    local_file_names = []
    uploaded_files = []

    if not ctx.message.attachments:
        return local_file_names # No attachments to process

    tasks = [
        handle_attachment(attachment, genai_client)
        for attachment in ctx.message.attachments
    ]
    try:
        results = await asyncio.gather(*tasks)

        # Process successful results
        for result_filenames, result_uploaded_files in results:
            local_file_names.extend(result_filenames)
            uploaded_files.extend(result_uploaded_files)
    except HandleAttachmentError as e:
        await send_long_message(
            ctx,
            f"Error: Failed to upload attachment(s). {e}",
            MAX_MESSAGE_LENGTH,
        )
        logger.exception("Failed to upload attachment(s).")
        return local_file_names # Return empty list on error

    if uploaded_files:
        for uploaded_file in uploaded_files:
            await wait_for_file_active(uploaded_file)
            logger.info(f"{uploaded_file.name} is active at server")
            final_prompt.append(
                Part.from_uri(
                    file_uri=uploaded_file.uri,
                    mime_type=uploaded_file.mime_type,
                ),
            )

    return local_file_names


async def prepend_author_info(
        ctx: commands.Context,
        final_prompt: list,
        formatted_time: str,
) -> None:
    """Prepends author/reply info to the prompt list."""
    prefix = ""
    if ctx.message.reference:
        try:
            # Fetch replied message to include its content
            replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            prefix = (
                f"{formatted_time}, {ctx.author.name} With Display Name "
                f'{ctx.author.display_name} and ID {ctx.author.id} '
                f'Replied to your message, "{replied.content}": '
            )
        except Exception:
            logger.exception("Failed to fetch replied message content.")
            # Fallback to just author info if fetching fails
            prefix = (
                f"{formatted_time}, {ctx.author.name} With Display Name "
                f"{ctx.author.display_name} and ID {ctx.author.id}: "
            )
    else:
        prefix = (
            f"{formatted_time}, {ctx.author.name} With Display Name "
            f"{ctx.author.display_name} and ID {ctx.author.id}: "
        )
    final_prompt.insert(0, prefix)


def process_youtube_links(message: str, final_prompt: list) -> None:
    """Find YouTube links in the original message.

    Then, adds them as FileData to the prompt.

    Args:
        message: the message you want to process
        final_prompt: the array of the final prompt

    """
    links = regex.finditer(YOUTUBE_PATTERN, message)
    if links:
        # Remove links from existing text parts first
        for i, part in enumerate(final_prompt):
            if isinstance(part, str):
                 final_prompt[i] = regex.sub(YOUTUBE_PATTERN, "", part)

        for link in links:
            url = repair_links(link.group())
            file = FileData(file_uri=url)
            logger.info(f"Found and Processed Link {url}")
            final_prompt.append(Part(file_data=file))


async def send_message_and_handle_status(
    chat: AsyncChat,
    final_prompt: list,
    ctx: commands.Context,
    safety_setting: str,
) -> tuple[
    GenerateContentResponse,
    list[Candidate],
    Candidate,
    FinishReason | None,
] | None:
    """Send the message to the chat and handles immediate finish reasons.

    Returns:
        A tuple (response, candidates, first_candidate, finish_reason) if successful,
        or None if processing should stop due to a handled finish reason.

    """
    response = await chat.send_message(final_prompt)
    candidates = response.candidates
    if not candidates:
         logger.warning("API returned no candidates.")
         await ctx.reply("The AI did not return a valid response.")
         return None

    first_candidate = candidates[0]
    finish_reason = first_candidate.finish_reason

    if finish_reason == FinishReason.MALFORMED_FUNCTION_CALL:
        logger.error("Function call is malformed!")
        await ctx.reply(
            "Seems like my function calling tool is malformed. Try again!",
        )
        return None

    if finish_reason == FinishReason.SAFETY:
        blocked_category = [
            HARM_PRETTY_NAME.get(safety.category.name, safety.category.name)
            for safety in first_candidate.safety_ratings
            if safety.probability in BLOCKED_CATEGORY.get(safety_setting, [])
        ]

        await ctx.reply(
            (
                f"This response was blocked due to "
                f"{', '.join(
                    blocked_category
                    if blocked_category
                    else ['a safety policy']
                )}"
            ),
            ephemeral=True,
        )
        logger.warning(
            f"Response blocked due to safety: {blocked_category}",
        )
        return None

    return response, candidates, first_candidate, finish_reason


async def process_response_parts(
    ctx: commands.Context,
    candidates: list,
    finish_reason: FinishReason,
    temp_config: dict,
    tools: list[Tool],
) -> list[str]:
    """Process the individual parts of the API response using handle_output."""
    output_file_names = []
    if not candidates or not candidates[0].content or not candidates[0].content.parts:
         logger.warning("No content parts found in response candidate.")
         await ctx.reply("The AI response had no content.")
         return output_file_names

    first_candidate = candidates[0]

    handle_whether_thought(first_candidate.content.parts)
    for part in first_candidate.content.parts:
        file_name_list = await handle_output(
            ctx,
            part,
            candidates,
            finish_reason,
            temp_config,
            tools,
        )
        output_file_names.extend(file_name_list)

    return output_file_names


def cleanup_files(file_names: list[str]) -> None:
    """Clean up local files generated during the process."""
    if file_names:
        for file in file_names:
            try:
                Path(file).unlink()
                logger.info(f"Deleted {Path(file).name} at local server")
            except OSError:
                 logger.exception(f"Failed to delete file {file}.")


def generate_audio_config(voice_name: str) -> GenerateContentConfig:
    """Generates a GenerateContentConfig for TTS models.

    Args:
        voice_name: The voice to use.

    Returns:
        GenerateContentConfig for a TTS.
    """
    return GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(
                    voice_name=voice_name,
                ),
            ),
        ),
    )
