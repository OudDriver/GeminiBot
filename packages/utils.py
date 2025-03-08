from datetime import timedelta
from typing import Any
from google.genai.types import Candidate
import time
import random
import string
import discord
import asyncio
import logging
import sys
import io
import re
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

def clean_text(text: str):
    """
    Replaces <sub></sub> and <sup></sup> tags with their Unicode subscript and superscript equivalents.

    Args:
        text: The input string containing <sub></sub> and <sup></sup> tags.

    Returns:
        The string with the tags replaced by subscript and superscript characters.
    """
    def replace_sub(m):
        return ''.join(subscript_map.get(c, c) for c in m.group(1))

    def replace_sup(m):
         return ''.join(superscript_map.get(c, c) for c in m.group(1))

    text = re.sub(r'<sub>(.*?)</sub>', replace_sub, text)
    text = re.sub(r'<sup>(.*?)</sup>', replace_sup, text)
    
    thought_matches = re.findall(r"<thought>[\s\S]*?</thought>", text)
    secret_matches = re.findall(r"<store>[\s\S]*?</store>", text)
    text = re.sub(r"<thought>[\s\S]*?</thought>", "", text)
    text = re.sub(r"<store>[\s\S]*?</store>", "", text)
    text = re.sub(r"\n<br>", "", text)
    
    return text, thought_matches, secret_matches

async def send_long_message(ctx, message, length):
    """Sends a long message in chunks, splitting at the nearest space within the length limit."""
    start = 0
    while start < len(message):
        end = min(start + length, len(message))  # Initial end position

        # Find the last space within the length limit
        if end < len(message):
            last_space = message.rfind(' ', start, end)
            if last_space != -1:
                end = last_space  # Split at the last space

        await ctx.reply(message[start:end])
        start = end + 1  # Move start to the next character after the split

async def send_image(ctx, file_name):
    """Sends an image from a path."""
    await ctx.reply(file=discord.File(file_name))

async def send_long_messages(ctx, messages, length):
    """Sends a long list of message in chunks, splitting at the nearest space within the length limit."""
    for message in messages:
        if isinstance(message, str):
            await send_long_message(ctx, message, length)
        elif isinstance(message, discord.File):
            await ctx.reply(file=message)
        
def timeout(member_id: str, duration: int, reason: str):
    """Timeouts a Discord member using their ID for a specified duration.

        Args:
            member_id: The user's ID.
            duration: Duration in seconds.
            reason: The reason why the user is timed out.
    """
    member_id = int(member_id)
    logging.info(f"Attempting to time out {member_id}")
    async def _mute(mem_id: int, dur: int, r: str = None):
        if dur <= 0:
            return "Time must be a positive integer"
        
        from commands.prompt import ctx_glob
        
        guild = ctx_glob.guild
        try:
            member = await guild.fetch_member(mem_id)
            if member is None:
                await ctx_glob.send("Member not found in this server.")
                return

            await member.timeout(timedelta(seconds=dur), reason=r)
            logging.info(f"Member with ID {mem_id} has been timed out for {dur} seconds. Reason: {r}")
            await ctx_glob.send(f"Member with ID {mem_id} has been timed out for {dur} seconds. Reason: {r}")
            return f"Successful! Member with ID {mem_id} has been timed out for {dur} seconds. Reason: {r}"
        except discord.Forbidden:
            logging.info("Missing Permission!")
            await ctx_glob.send("Missing Permission!")
            return f"Missing Permissions. Ping <@{ctx_glob.guild.owner.id}> to fix."
        except discord.HTTPException as e:
            logging.info(e)
            await ctx_glob.send(e)
            return f"{e}. If it is 404, double check the user ID input, got {member_id}."
        
    loop = asyncio.get_running_loop()
    try:
        return loop.run_until_complete(_mute(member_id, duration, reason))
    except RuntimeError as e:
        logging.error(e)

def send(message: str):
    async def _send(msg):
        from commands.prompt import ctx_glob
        await ctx_glob.send(msg)
        
    loop = asyncio.get_running_loop() 
    loop.run_until_complete(_send(message))

# It's useless now but may not be useless in the near future... Maybe.
def format_args(args: dict[str: Any]) -> dict[str: Any]:
    formatted = {}
    for key, val in args.items():
        formatted[key] = val
    return formatted

def hi():
    """
    A test function that says hi.
    """
    send("SassBot Said Hi!")
    logging.info("SassBot Said Hi!")
    return "SassBot Said Hi!"
    
def execute_code(code_string: str):
    """Executes Python code from a string and captures the output. Only supports Python.

    Args:
        code_string: The string containing the Python code to execute.

    Returns:
        The standard output or standard error captured during code execution
    """
    from commands.prompt import ctx_glob

    async def reply(msg):
        await ctx_glob.reply(msg)

    loop = asyncio.get_event_loop()
    
    encoded_string = code_string.encode().decode('unicode_escape')

    # Redirect stdout and stderr to capture output
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = captured_stdout = io.StringIO()
    sys.stderr = captured_stderr = io.StringIO()

    # Use provided global_namespace or create a new one
    global_namespace = {}

    try:
        # Execute the code in the custom global namespace
        exec(encoded_string, global_namespace)
    except Exception as e:
        # Capture the error message
        captured_stderr.write(f"{e}")
        final = f"Code:\n```py\n{encoded_string}\n```\nError:\n```{captured_stderr.getvalue()}```"
        
        logging.info(captured_stderr.getvalue())

        try:
            loop.run_until_complete(reply(final))
        except RuntimeError as e:
            logging.error(e)
        
        return captured_stderr.getvalue()
    finally:
        # Restore stdout and stderr
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

