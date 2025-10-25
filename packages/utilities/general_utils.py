from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import discord
import nest_asyncio
import regex

from packages.maps import SUBSCRIPT_MAP, SUPERSCRIPT_MAP

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
    if not extension:
        msg = "No extension provided!"
        raise ValueError(msg)

    extension = extension.removeprefix(".")

    timestamp = int(time.time())
    random_str = uuid.uuid4()
    return f"{timestamp}_{random_str}.{extension}"


def convert_subscripts(text: str) -> str:
    """Finds all <sub></sub> tags and converts their content to subscript characters.

    Args:
        text: The input string containing <sub> tags.

    Returns:
        A new string with subscript tags replaced by Unicode characters.
    """
    def replacer(match: regex.Match) -> str:
        """A nested function to handle the replacement logic."""
        content = match.group(1)
        return "".join(SUBSCRIPT_MAP.get(char, char) for char in content)

    return regex.compile(r"<sub>(.*?)</sub>").sub(replacer, text)


def convert_superscripts(text: str) -> str:
    """Finds all <sup></sup> tags and converts their content to superscript characters.

    Args:
        text: The input string containing <sub> tags.

    Returns:
        A new string with subscript tags replaced by Unicode characters.
    """
    def replacer(match: regex.Match) -> str:
        """A nested function to handle the replacement logic."""
        content = match.group(1)
        return "".join(SUPERSCRIPT_MAP.get(char, char) for char in content)

    return regex.compile(r"<sup>(.*?)</sup>").sub(replacer, text)


def clean_text(text: str) -> tuple[str, list[str]]:
    """Clean a string.

    It will replace <sub></sub> and <sup></sup> to their respective Unicode.
    It removes all instances of <store></store> tags, which stores secrets.

    Args:
        text: The input string containing <sub></sub> and <sup></sup> tags.

    Returns:
        The string with the tags replaced by subscript and superscript characters.

    """
    text = convert_subscripts(text)
    text = convert_superscripts(text)

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
    if length <= 0:
        msg = "Length limit must be positive."
        raise ValueError(msg)

    if not message:
        return

    start = 0
    while start < len(message):
        # Determine the maximum possible end for this chunk
        potential_end = min(start + length, len(message))

        # If this chunk potentially goes beyond the message end, we take it all
        if potential_end == len(message):
            end = potential_end
            next_start = end
        else:
            # Otherwise, try to find the last space within the limit
            last_space = message.rfind(" ", start, potential_end)

            if last_space > start:
                end = last_space
                next_start = end + 1
            else:
                end = potential_end
                next_start = end

        chunk = message[start:end].strip()

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
        msg = "Message is empty!"
        raise ValueError(msg)

    # Use the generator to get chunks and send them
    for chunk in split_message_chunks(message, length):
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
        messages: str | list[str | discord.File],
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
    if isinstance(messages, str):
        await send_long_message(ctx, messages, length)
        return

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
