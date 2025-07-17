from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import discord
import nest_asyncio
import regex

from packages.maps import subscript_map, superscript_map

if TYPE_CHECKING:
    from collections.abc import Iterator

    from discord.ext.commands import Context
    from google.genai.types import Candidate

nest_asyncio.apply()


def generate_unique_file_name(extension: str) -> str:
    """Generate a unique filename using the current timestamp and a random string.

    Args:
        extension: The extension you want to use (e.g. png, jpg, etc.)

    Returns:
        A random file name.

    """
    timestamp = int(time.time())
    random_str = uuid.uuid4()
    return f"{timestamp}_{random_str}.{extension}"


def replace_subscript_tags(match_obj: regex.Match) -> str:
    """Replace <sub></sub> text to an actual subscript.

    Callback function for regex.sub to convert characters in a captured group
    (match_obj.group(1)) to their subscript equivalents using `subscript_map`.

    Characters not found in the subscript_map are left unchanged.

    Args:
        match_obj: A regular expression match object. This function
                   specifically processes the content of the first
                   capturing group (match_obj.group(1)).

    Returns:
        The string from match_obj.group(1) with applicable characters
        replaced by their subscript versions.

    """
    # Get the string captured by the first group in the regex match
    content_to_convert = match_obj.group(1)

    converted_chars = (
        subscript_map.get(char, char) for char in content_to_convert
    )

    # Join the list of converted (or original) characters back into a single string
    return "".join(converted_chars)


def replace_superscript_tags(match_obj: regex.Match) -> str:
    """Replace <sup></sup> text to an actual script.

    Callback function for regex.sub to convert characters in a captured group
    (match_obj.group(1)) to their subscript equivalents using `superscript_map`.

    Characters not found in the superscript_map are left unchanged.

    Args:
        match_obj: A regular expression match object. This function
                   specifically processes the content of the first
                   capturing group (match_obj.group(1)).

    Returns:
        The string from match_obj.group(1) with applicable characters
        replaced by their subscript versions.

    """
    # Get the string captured by the first group in the regex match
    content_to_convert = match_obj.group(1)

    converted_chars = (superscript_map.get(char, char) for char in content_to_convert)

    # Join the list of converted (or original) characters back into a single string
    return "".join(converted_chars)


def clean_text(text: str) -> tuple[str, list[str]]:
    """Clean a string.

    It will replace <sub></sub> and <sup></sup> to their respective Unicode.
    It removes all instances of <store></store> tags, which stores secrets.

    Args:
        text: The input string containing <sub></sub> and <sup></sup> tags.

    Returns:
        The string with the tags replaced by subscript and superscript characters.

    """
    text = regex.sub(r"<sub>(.*?)</sub>", replace_subscript_tags, text)
    text = regex.sub(r"<sup>(.*?)</sup>", replace_superscript_tags, text)

    secret_matches = regex.findall(r"<store>[\s\S]*?</store>", text)
    text = regex.sub(r"<store>[\s\S]*?</store>", "", text)

    return text, secret_matches


def split_message_chunks(message: str, length: int) -> Iterator[str]:
    """Split a long message into chunks based on length, preferring spaces.

    Args:
        message: The message string to split.
        length: The maximum length of each chunk.

    Yields:
        str: The next chunk of the message.

    """
    if not message:
        return # Return an empty iterator if the message is empty

    start = 0
    while start < len(message):
        # Determine the maximum possible end for this chunk
        potential_end = min(start + length, len(message))

        # If this chunk potentially goes beyond the message end, we take it all
        if potential_end == len(message):
            end = potential_end
            next_start = end # Loop will terminate
        else:
            # Otherwise, try to find the last space within the limit
            # [start, potential_end)
            # We search *before* potential_end
            # to allow splitting exactly at 'length' if needed.
            last_space = message.rfind(" ", start, potential_end)

            # If a space is found *after* the current start position, split there
            if last_space > start:
                end = last_space
                next_start = end + 1 # Start after the space for the next chunk
            else:
                # No suitable space found, or space is at the very beginning.
                # Cut at the maximum length (potential_end).
                end = potential_end
                next_start = end

        chunk = message[start:end]
        if chunk:
            yield chunk

        start = next_start


async def send_long_message(ctx: Context, message: str, length: int) -> None:
    """Send a long message in chunks using a helper generator.

    Args:
        ctx: The context of the command invocation.
        message: The message you want to send.
        length: The length limit of each message chunk.

    """
    if check_message_empty(message):
        return

    if length <= 0:
        msg = "Length limit must be positive."
        raise ValueError(msg)

    # Use the generator to get chunks and send them
    for chunk in split_message_chunks(message, length):
        # The generator ensures chunks aren't empty
        # unless the original message was empty
        # (and the generator handles empty message case by returning immediately)
        await ctx.reply(chunk)


async def send_file(ctx: Context, file_name: str) -> None:
    """Send an image from a path.

    Args:
        ctx: The context of the command invocation.
        file_name: The name of the file.

    """
    await ctx.reply(file=discord.File(file_name))


async def send_long_messages(
        ctx: Context,
        messages: list[str | discord.File],
        length: int,
) -> None:
    """Send a long list of message in chunks.

    Splits at the nearest space within the length limit.

    Args:
        ctx: The context of the command invocation.
        messages: A list of messages to send,
                  whether it's an image or a normal text.
        length: The length limit of each message chunk.

    """
    for message in messages:
        if isinstance(message, str):
            if check_message_empty(message):
                continue
            await send_long_message(ctx, message, length)
        elif isinstance(message, discord.File):
            await ctx.reply(file=message)


def create_grounding_markdown(candidate: Candidate) -> str | None:
    """Parse a candidate and creates a markdown string of grounding sources.

    Args:
        candidate: The candidate to parse.

    Returns:
        str: A markdown string of grounding sources,
             or None if no grounding data is found.

    """
    grounding_chunks = candidate.grounding_metadata.grounding_chunks

    if not grounding_chunks:
        return None

    markdown_string = "## Grounding Sources:\n\n"

    for chunk in grounding_chunks:
        markdown_string += f"- [{chunk.web.title}]({chunk.web.uri})\n"

    return markdown_string


def check_message_empty(message: str) -> bool:
    """Check if a message is empty.

    It includes check such as an empty string, only whitespaces, and only newlines.

    Args:
        message: The message to check

    Returns:
        True if it is empty, and False otherwise.

    """
    if not message:
        return True

    stripped_message = message.strip()
    if not stripped_message:
        return True

    return bool(regex.fullmatch(r"[\r\n]+", message))


def repair_links(link: str) -> str:
    """Add https:// when it is missing on the beginning of a link.

    Args:
        link: The link to fix

    Returns:
        The fixed link.

    """
    if not regex.search(r"^http", link):
        return "https://" + link
    return link


def remove_thought_tags(thought: str) -> str:
    """Remove thought tags from a thought.

    Args:
        thought: The thought to remove the thought tags.

    """
    thought_pattern = r"<thought>|</thought>"
    reg = regex.compile(thought_pattern)

    return regex.sub(reg, "", thought)


def ensure_list(obj: object) -> list:
    """Ensures if an object is a list.

    If an object is not a list, wrap that object in a list.
    Otherwise, return itself.

    Args:
        obj: The object.

    Returns:
        A guaranteed list.
    """
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    return [obj]
