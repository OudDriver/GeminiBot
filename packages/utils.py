import json
import traceback
import uuid

from google.genai.types import Candidate
import time
import random
import string
import discord
import asyncio
import logging
import requests
import regex
import nest_asyncio
import subprocess
import platform

from packages.maps import subscript_map, superscript_map
import docker
import docker.errors

nest_asyncio.apply()


def generate_unique_file_name(extension: str):
    """
    Generates a unique filename using the current timestamp and a random string.
    """
    timestamp = int(time.time())
    random_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{random_str}.{extension}"


def replace_sub(m):
    return "".join(subscript_map.get(c, c) for c in m.group(1))


def replace_sup(m):
    return "".join(superscript_map.get(c, c) for c in m.group(1))


def clean_text(text: str):
    """
    Replaces <sub></sub> and <sup></sup> tags with their Unicode subscript and superscript equivalents.

    Args:
        text: The input string containing <sub></sub> and <sup></sup> tags.

    Returns:
        The string with the tags replaced by subscript and superscript characters.
    """

    text = regex.sub(r"<sub>(.*?)</sub>", replace_sub, text)
    text = regex.sub(r"<sup>(.*?)</sup>", replace_sup, text)

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
            last_space = message.rfind(" ", start, end)
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


def reply(message: str):
    async def _reply(msg):
        from commands.prompt import ctx_glob

        await ctx_glob.reply(msg)

    loop = asyncio.get_running_loop()
    loop.run_until_complete(_reply(message))


def start_docker_daemon():
    """
    Attempts to start the Docker daemon on Windows, Linux, and macOS.

    Returns:
        bool: True if the Docker daemon appears to have started successfully,
              False otherwise.  It returns True also if docker is already running
    """

    os_name = platform.system()

    try:
        if os_name == "Linux":
            subprocess.run(
                ["sudo", "docker", "info"], check=True, capture_output=True, text=True
            )
        else:
            subprocess.run(
                ["docker", "info"], check=True, capture_output=True, text=True
            )
        logging.info("Docker is already running.")
        return True

    except subprocess.CalledProcessError:
        logging.warning("Docker is not running. Attempting to start...")

        try:
            if os_name == "Windows":
                docker_desktop_path = (
                    r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
                )
                subprocess.run(
                    [docker_desktop_path], check=True, capture_output=True, text=True
                )
                logging.info("Docker started on Windows.")
                return True
            elif os_name == "Linux":
                subprocess.run(
                    ["sudo", "systemctl", "start", "docker"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logging.info("Docker started on Linux.")
                return True
            elif os_name == "Darwin":  # macOS
                subprocess.run(
                    ["open", "/Applications/Docker.app"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logging.info("Docker started on macOS.")
                return True
            else:
                logging.info(f"Unsupported operating system: {os_name}")
                return False

        except subprocess.CalledProcessError as e:
            logging.error(f"Error starting Docker on {os_name}: {e}")
            return False
        except FileNotFoundError as e:
            print(f"Docker Desktop not found. {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False


def execute_code(code_string: str) -> str | None:
    """Executes Python code. Times out in 5 seconds.

    Args:
        code_string: The Python code to execute.

    Returns:
        The captured output (stdout and stderr).
    """
    timeout_seconds = 5
    encoded_string = code_string.encode().decode("unicode_escape")

    container_name = f"python-sandbox-{uuid.uuid4()}"
    image_name = "python-sandbox-image"  # Make image name a variable
    client = None

    try:
        try:
            client = docker.from_env()

            client.ping()
            logging.info("Successfully connected to Docker daemon.")

        except (requests.exceptions.ConnectionError, docker.errors.APIError) as e:
            log_msg = f"Docker Daemon Connection Error (ping failed): {traceback.format_exc()}"
            logging.error(log_msg)
            reply_msg = (
                f"Error connecting to Docker daemon: {e}. "
                "Please ensure Docker Desktop (or the Docker daemon service) "
                "is running and responsive."
            )
            save_temp_config(
                tool_use={
                    "name": "Execute Code (Error)",
                    "input": code_string,
                    "output": reply_msg,
                }
            )
            reply(reply_msg)
            return reply_msg  # Return early, cannot proceed
        except docker.errors.DockerException as e:
            # Catches other Docker-related errors during client initialization
            log_msg = f"Failed to initialize Docker client: {traceback.format_exc()}"
            logging.error(log_msg)
            reply_msg = f"Error initializing Docker client: {e}. Is Docker installed correctly and the service running?"
            reply(reply_msg)
            save_temp_config(
                tool_use={
                    "name": "Execute Code (Error)",
                    "input": code_string,
                    "output": reply_msg,
                }
            )
            return reply_msg  # Return early
        except Exception as e:  # Catch any other unexpected error during init/ping
            log_msg = f"Unexpected error initializing Docker or pinging daemon: {traceback.format_exc()}"
            logging.error(log_msg)
            reply_msg = f"Unexpected error connecting to Docker: {e}"
            save_temp_config(
                tool_use={
                    "name": "Execute Code (Error)",
                    "input": code_string,
                    "output": reply_msg,
                }
            )
            reply(reply_msg)
            return reply_msg  # Return early

        try:
            client.images.get(image_name)
            logging.info(f"Required Docker image '{image_name}' found.")
        except docker.errors.ImageNotFound:
            log_msg = f"Required Docker image '{image_name}' not found."
            logging.error(log_msg)
            reply_msg = (
                f"Error: The required Docker image '{image_name}' was not found locally. "
                f"Please build or pull the image before running the code execution."
            )
            save_temp_config(
                tool_use={
                    "name": "Execute Code (Error)",
                    "input": code_string,
                    "output": reply_msg,
                }
            )
            reply(reply_msg)
            return reply_msg
        except docker.errors.APIError as e:
            log_msg = f"Docker API Error checking for image '{image_name}': {traceback.format_exc()}"
            logging.error(log_msg)
            reply_msg = f"Error checking for Docker image '{image_name}': {e}"
            save_temp_config(
                tool_use={
                    "name": "Execute Code (Error)",
                    "input": code_string,
                    "output": reply_msg,
                }
            )
            reply(reply_msg)
            return reply_msg

        container = client.containers.run(
            "python-sandbox-image",
            command=["python", "-c", code_string],
            detach=True,
            mem_limit="128m",
            cpu_shares=102,
            name=container_name,
            network_disabled=True,
            read_only=True,
            stderr=True,
        )

        result = container.wait(timeout=timeout_seconds)
        exit_code = result.get("StatusCode", -1)  # Default to -1 if key missing

        # Capture output (stdout and stderr)
        output = container.logs().decode(errors="replace")

        if exit_code != 0:
            # Append error message if the container exited abnormally
            output += f"\nERROR: Container exited with status code: {exit_code}"

        final = (
            f"Code:\n```py\n{encoded_string}\n```\nOutput:\n```\n{output.strip()}\n```"
        )
        logging.info(final)
        reply(final)

        save_temp_config(
            tool_use={
                "name": "Execute Code",
                "input": code_string,
                "output": final,
            }
        )

        return output.strip()

    except docker.errors.ContainerError as e:
        logging.error(f"Container Error: {traceback.format_exc()}")
        save_temp_config(
            tool_use={
                "name": "Execute Code (Error)",
                "input": code_string,
                "output": f"Container Error: {e}",
            }
        )
        reply(f"Container Error: {e}")
        return f"Container Error: {e}"
    except docker.errors.ImageNotFound as e:
        logging.error(f"Image Not Found Error: {traceback.format_exc()}")
        save_temp_config(
            tool_use={
                "name": "Execute Code (Error)",
                "input": code_string,
                "output": f"Image Not Found Error: {e}",
            }
        )
        reply(f"Image Not Found Error: {e}")
        return f"Image Not Found Error: {e}"
    except docker.errors.APIError as e:
        logging.error(f"Docker API Error: {traceback.format_exc()}")
        save_temp_config(
            tool_use={
                "name": "Execute Code (Error)",
                "input": code_string,
                "output": f"Docker API Error: {e}",
            }
        )
        reply(f"Docker API Error: {e}")
        return f"Docker API Error: {e}"
    except requests.exceptions.ConnectionError as e:
        log_msg = f"Docker Daemon Connection Error (likely timeout during wait): {traceback.format_exc()}"
        logging.error(log_msg)
        save_temp_config(
            tool_use={
                "name": "Execute Code (Error)",
                "input": code_string,
                "output": f"Docker API Error: {e}",
            }
        )
        reply_msg = f"Error communicating with Docker: {e}. It might be slow or unresponsive or it timed out."
        reply(reply_msg)
        return reply_msg
    except Exception as e:
        logging.error(f"An unexpected error: {traceback.format_exc()}")
        save_temp_config(
            tool_use={
                "name": "Execute Code (Error)",
                "input": code_string,
                "output": f"An unexpected error: {e}",
            }
        )
        reply(f"An unexpected error: {e}")
        return f"An unexpected error: {e}"
    finally:
        try:
            container = client.containers.get(container_name)
            container.remove(force=True)  # Make sure it is cleaned up
        except Exception:
            pass


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
    if not regex.search(r"^http", link):
        return "https://" + link
    return link


def save_temp_config(
    model: str | None = None,
    system_prompt_data: str | None = None,
    current_uwu_status: str | None = None,
    thought: list | None = None,
    secret: list | str | None = None,
    tool_use: dict | None = None,
):
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
        "system_prompt": system_prompt_data
        if system_prompt_data is not None
        else existing_config.get("system_prompt", None),
        "uwu": current_uwu_status
        if current_uwu_status is not None
        else existing_config.get("uwu", None),
        "thought": thought
        if thought is not None
        else existing_config.get("thought", None),
        "secret": [],
        "tools_history": [],
    }

    # Handle 'secret' (append to the list, or create a new list)
    if secret is not None:
        existing_secrets = existing_config.get(
            "secret", []
        )  # Get existing list, default to empty list
        if isinstance(existing_secrets, list):
            if isinstance(secret, list):
                new_config["secret"] = existing_secrets + secret  # append the list
            else:
                new_config["secret"] = existing_secrets + [
                    secret
                ]  # Append the new secret
        else:
            # Handle the case where 'secret' exists but is not a list.
            # We'll overwrite it with a new list containing the provided secret.
            if isinstance(secret, list):
                new_config["secret"] = secret
            else:
                new_config["secret"] = [secret]
    else:
        new_config["secret"] = existing_config.get("secret", None)  # keep it as is

        # Handle 'secret' (append to the list, or create a new list)
        if secret is not None:
            existing_secrets = existing_config.get(
                "secret", []
            )  # Get existing list, default to empty list
            if isinstance(existing_secrets, list):
                if isinstance(secret, list):
                    new_config["secret"] = existing_secrets + secret  # append the list
                else:
                    new_config["secret"] = existing_secrets + [
                        secret
                    ]  # Append the new secret
            else:
                # Handle the case where 'secret' exists but is not a list.
                # We'll overwrite it with a new list containing the provided secret.
                if isinstance(secret, list):
                    new_config["secret"] = secret
                else:
                    new_config["secret"] = [secret]
        else:
            new_config["secret"] = existing_config.get("secret", None)  # keep it as is

        # Handle 'tools_history' (append to the list, or create a new list)
        if tool_use is not None:
            if tool_use != {}:
                existing_history = existing_config.get("tools_history", [])
                if isinstance(existing_history, list):
                    new_config["tools_history"].append(tool_use)
                else:
                    new_config["tools_history"] = [tool_use]
            else:
                new_config["tools_history"] = []


        else:
            new_config["tools_history"] = existing_config.get("tools_history", None)
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
        with open(temp_config_path) as f:
            config = json.load(f)
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(e)
        return {}  # Return an empty dictionary if the file is missing or invalid

def remove_thought_tags(thought: str):
    thought_pattern = r'<thought>|</thought>'
    reg = regex.compile(thought_pattern)

    return regex.sub(reg, "", thought)