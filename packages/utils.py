import json
from google.genai.types import Candidate
import time
import random
import string
import discord
import asyncio
import logging
import sys
import io
import regex
import nest_asyncio

from packages.maps import subscript_map, superscript_map

nest_asyncio.apply()

def generate_unique_file_name(extension: str):
    """
    Generates a unique filename using the current timestamp and a random string.
    """
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{random_str}.{extension}"

def replace_sub(m):
    return ''.join(subscript_map.get(c, c) for c in m.group(1))

def replace_sup(m):
     return ''.join(superscript_map.get(c, c) for c in m.group(1))

def clean_text(text: str):
    """
    Replaces <sub></sub> and <sup></sup> tags with their Unicode subscript and superscript equivalents.

    Args:
        text: The input string containing <sub></sub> and <sup></sup> tags.

    Returns:
        The string with the tags replaced by subscript and superscript characters.
    """

    text = regex.sub(r'<sub>(.*?)</sub>', replace_sub, text)
    text = regex.sub(r'<sup>(.*?)</sup>', replace_sup, text)

    thought_matches = regex.findall(r"<thought>[\s\S]*?</thought>", text)
    secret_matches = regex.findall(r"<store>[\s\S]*?</store>", text)
    text = regex.sub(r"<thought>[\s\S]*?</thought>", "", text)
    text = regex.sub(r"<store>[\s\S]*?</store>", "", text)

    return text, thought_matches, secret_matches

async def send_long_message(ctx, message, length):
    """Sends a long message in chunks, splitting at the nearest space within the length limit."""
    start = 0
    while start < len(message):
        end = min(start + length, len(message))
        if end < len(message):
            last_space = message.rfind(' ', start, end)
            if last_space != -1:
                end = last_space  

        await ctx.reply(message[start:end])
        start = end + 1  

async def send_image(ctx, file_name):
    """Sends an image from a path."""
    await ctx.reply(file=discord.File(file_name))

async def send_long_messages(ctx, messages, length):
    """Sends a long list of message in chunks, splitting at the nearest space within the length limit."""
    for message in messages:
        if isinstance(message, str):
            if check_message_empty(message):
                continue
            await send_long_message(ctx, message, length)
        elif isinstance(message, discord.File):
            await ctx.reply(file=message)

async def reply(msg):
    from commands.prompt import ctx_glob
    await ctx_glob.reply(msg)

def execute_code(code_string: str):
    """Executes Python code from a string and captures the output. Only supports Python.

    Args:
        code_string: The string containing the Python code to execute.

    Returns:
        The standard output or standard error captured during code execution
    """

    loop = asyncio.get_event_loop()
    
    encoded_string = code_string.encode().decode('unicode_escape')
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = captured_stdout = io.StringIO()
    sys.stderr = captured_stderr = io.StringIO()

    global_namespace = {}

    try:
        exec(encoded_string, global_namespace)
    except Exception as e:
        captured_stderr.write(f"{e}")
        final = f"Code:\n```py\n{encoded_string}\n```\nError:\n```{captured_stderr.getvalue()}```"
        
        logging.info(captured_stderr.getvalue())

        try:
            loop.run_until_complete(reply(final))
        except RuntimeError as e:
            logging.error(e)
        
        return captured_stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    captured = captured_stdout.getvalue()

    final = f"Code:\n```py\n{encoded_string}\n```\nOutput:\n```\n{captured}```"

    logging.info(final)
    try:
        loop.run_until_complete(reply(final))
    except RuntimeError as e:
        logging.error(e)

    return captured

def create_grounding_markdown(candidates: list[Candidate]):
    """
    Parses JSON data and creates a markdown string of grounding sources.

    Args:
        candidates (dict): The JSON data to parse.

    Returns:
        str: A markdown string of grounding sources, or None if no grounding data is found.
    """

    try:
        grounding_chunks = candidates[0].grounding_metadata.grounding_chunks
    except AttributeError as e:
        return e

    if not grounding_chunks:
        return

    markdown_string = "## Grounding Sources:\n\n"

    for chunk in grounding_chunks:
        markdown_string += f"- [{chunk.web.title}]({chunk.web.uri})\n"

    return markdown_string

def check_message_empty(message: str) -> bool:
    if not message:
        return True

    stripped_message = message.strip()
    if not stripped_message:
        return True

    if regex.fullmatch(r"[\r\n]+", message):
        return True

    return False

def repair_links(link: str):
    if not regex.search(r'^http', link):
        return "https://" + link
    return link

def save_temp_config(model: str | None=None, system_prompt_data: str | None=None, current_uwu_status: str | None=None, thought: list | None=None, secret: list | None=None):
    """Saves the current configuration to temp_config.json.

    If an argument is None, uses the existing value from the file (if it exists).
    For the 'secret' argument, if a value is provided, it appends it to the
    existing list of secrets (or creates a new list if none exists).
    """

    temp_config_path = "temp/temp_config.json"

    # Load existing configuration
    existing_config = read_temp_config()

    # Update configuration, handling 'secret' specially.
    new_config = {
        "model": model if model is not None else existing_config.get("model", None),
        "system_prompt": system_prompt_data if system_prompt_data is not None else existing_config.get("system_prompt", None),
        "uwu": current_uwu_status if current_uwu_status is not None else existing_config.get("uwu", None),
        "thought": thought if thought is not None else existing_config.get("thought", None)
    }

    # Handle 'secret' (append to the list, or create a new list)
    if secret is not None:
        existing_secrets = existing_config.get("secret", [])  # Get existing list, default to empty list
        if isinstance(existing_secrets, list):
            if isinstance(secret, list):
                new_config["secret"] = existing_secrets + secret # append the list
            else:
                new_config["secret"] = existing_secrets + [secret]  # Append the new secret
        else:
            # Handle the case where 'secret' exists but is not a list.
            #  We'll overwrite it with a new list containing the provided secret.
            if isinstance(secret, list):
                 new_config["secret"] = secret
            else:
                new_config["secret"] = [secret]
    else:
        new_config["secret"] = existing_config.get("secret", None) # keep it as is

    # Save the updated configuration
    with open(temp_config_path, "w") as f:
        json.dump(new_config, f)


def read_temp_config():
    """Reads the configuration from temp/temp_config.json.

    Returns:
        dict: A dictionary containing the configuration, or an empty dictionary
              if the file doesn't exist or contains invalid JSON.
    """
    temp_config_path = "temp/temp_config.json"

    try:
        with open(temp_config_path, "r") as f:
            config = json.load(f)
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(e)
        return {}  # Return an empty dictionary if the file is missing or invalid

def remove_thought_tags(thought: str):
    thought_pattern = r'<thought>|</thought>'
    reg = regex.compile(thought_pattern)

    return regex.sub(reg, "", thought)