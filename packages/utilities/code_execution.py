# from __future__ import annotations # Breaks Automatic Schema Definition # noqa: ERA001

import asyncio
import logging
import platform
import subprocess
import uuid

import docker
import nest_asyncio
import requests
from docker import DockerClient, errors

from packages.utilities.errors import (
    DockerConnectionError,
    DockerContainerError,
    DockerExecutionError,
    DockerImageNotFoundError,
)
from packages.utilities.file_utils import save_temp_config

logger = logging.getLogger(__name__)
nest_asyncio.apply()

def reply(message: str) -> None:
    """Reply using the global variable from commands.prompt.

    Args:
        message: The message to reply.

    """
    async def _reply(msg: str) -> None:
        from commands.prompt import ctx_glob

        await ctx_glob.reply(msg)

    loop = asyncio.get_running_loop()
    loop.run_until_complete(_reply(message))


def start_docker_daemon() -> bool:
    """Attempt to start the Docker daemon on Windows, Linux, and macOS.

    Returns:
        bool: True if the Docker daemon appears to have started successfully,
              False otherwise.  It returns True also if docker is already running

    """
    os_name = platform.system()

    is_running = False
    try:
        if os_name == "Linux":
            subprocess.run(
                ["sudo", "docker", "info"],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            subprocess.run(
                ["docker", "info"],
                check=True,
                capture_output=True,
                text=True,
            )
        logger.info("Docker is already running.")
        return True

    except subprocess.CalledProcessError:
        logger.warning("Docker is not running. Attempting to start...")

        try:
            if os_name == "Windows":
                docker_desktop_path = (
                    r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
                )
                subprocess.run(
                    [docker_desktop_path], check=True, capture_output=True, text=True,
                )
                logger.info("Docker started on Windows.")
                is_running = True
            elif os_name == "Linux":
                subprocess.run(
                    ["sudo", "systemctl", "start", "docker"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("Docker started on Linux.")
                is_running = True
            elif os_name == "Darwin":  # macOS
                subprocess.run(
                    ["open", "/Applications/Docker.app"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("Docker started on macOS.")
                is_running = True
            else:
                logger.info(f"Unsupported operating system: {os_name}")

        except subprocess.CalledProcessError:
            logger.exception("Error starting Docker on {os_name}.")
            return False
        except FileNotFoundError:
            logger.exception("Docker Desktop not found.")
            return False
        except Exception:
            logger.exception("An unexpected error occurred.")
            return False

        return is_running


def _get_docker_client() -> DockerClient | None:  # noqa: FA102
    """Connect to Docker and pings the daemon."""
    try:
        client = docker.from_env()
        client.ping()
        logger.info("Successfully connected to Docker daemon.")
        return client
    except (requests.exceptions.ConnectionError, errors.APIError) as e:
        msg = (
            f"Docker Daemon Connection Error (ping failed): {e}. "
            "Ensure Docker is running and responsive."
        )
        raise DockerConnectionError(msg) from e
    except errors.DockerException as e:
        msg = (
            f"Failed to initialize Docker client: {e}. "
            "Is Docker installed correctly and the service running?"
        )
        raise DockerConnectionError(msg) from e
    except Exception as e:
        msg = f"Unexpected error initializing Docker or pinging daemon: {e}"
        raise DockerConnectionError(msg) from e


def _check_docker_image(client: DockerClient, image_name: str) -> None:
    """Check if the required Docker image exists."""
    try:
        client.images.get(image_name)
        logger.info(f"Required Docker image '{image_name}' found.")
    except errors.ImageNotFound as e:
        msg = (
            f"Required Docker image '{image_name}' not found locally. "
            "Please build or pull the image."
        )
        raise DockerImageNotFoundError(msg) from e
    except errors.APIError as e:
        msg = f"Docker API Error checking for image '{image_name}': {e}"
        raise DockerContainerError(msg) from e
    except Exception as e:
         msg = f"Unexpected error checking for image '{image_name}': {e}"
         raise DockerContainerError(msg) from e

def _run_in_container(
        client: DockerClient,
        image_name: str,
        code_string: str,
        timeout_seconds: int,
) -> str | None:  # noqa: FA102
    """Run the code in a Docker container and returns the output."""
    container_name = f"python-sandbox-{uuid.uuid4()}"
    container = None

    try:
        container = client.containers.run(
            image_name,
            command=["python", "-c", code_string],
            detach=True,
            mem_limit="128m",
            cpu_shares=102, # Consider making these configurable
            name=container_name,
            network_disabled=True,
            read_only=True,
            stderr=True,
        )

        result = container.wait(timeout=timeout_seconds)
        exit_code = result.get("StatusCode", -1)
        output = container.logs(stdout=True, stderr=True).decode(errors="replace")

        if exit_code != 0:
            output += f"\nERROR: Container exited with status code: {exit_code}"

        return output.strip()

    except errors.ContainerError as e:
        # This often includes stderr output from the container process itself
        # noinspection PyUnresolvedReferences
        # Type hinting is wrong.
        output = e.stderr.decode(errors="replace") if e.stderr else str(e)
        logger.exception(f"ContainerError executing code. Output/Error: {output}")
        msg = f"Container Error (Exit Code: {e.exit_status}):\n{output.strip()}"
        raise DockerContainerError(msg) from e
    except errors.APIError as e:
        logger.exception("Docker API Error during container run/wait.")
        msg = f"Docker API Error during execution: {e}"
        raise DockerContainerError(msg) from e
    except requests.exceptions.ConnectionError as e:
        # This typically happens if the wait() times out
        logger.exception("Timeout or connection error waiting for container.")
        msg = f"Execution timed out after {timeout_seconds} seconds or connection lost."
        raise DockerContainerError(msg) from e
    except Exception as e:
        logger.exception("Unexpected error during container execution.")
        msg = f"Unexpected container error: {e}"
        raise DockerContainerError(msg) from e
    finally:
        if container:
            try:
                container.remove(force=True)
                logger.info(f"Removed container {container_name}")
            except errors.NotFound:
                logger.warning(f"Container {container_name} already removed.")
            except errors.APIError:
                logger.exception(f"API error removing container {container_name}")
            except Exception:
                logger.exception(
                    f"Unexpected error removing container {container_name}",
                )


def execute_code(code_string: str) -> str:
    """Execute Python code in a Docker container. Times out in 5 seconds.

    Args:
        code_string: The Python code to execute.

    Returns:
        The captured output (stdout and stderr) or an error message.

    """
    timeout_seconds = 5
    image_name = "python-sandbox-image"
    encoded_string = code_string.encode().decode("unicode_escape")

    try:
        # 1. Get Docker Client
        client = _get_docker_client()

        # 2. Check for Image
        _check_docker_image(client, image_name)

        # 3. Run Code in Container
        output = _run_in_container(client, image_name, code_string, timeout_seconds)

        # Success Case
        final_reply = (
            f"Code:\n```py\n{encoded_string}\n```\nOutput:\n```\n{output}\n```"
        )
        logger.info(f"Execution successful. Output length: {len(output)}")
        reply(final_reply)
        save_temp_config(
            tool_use={
                "name": "Execute Code",
                "input": code_string,
                "output": final_reply,
            },
        )
        return output # Return just the raw output

    except DockerExecutionError as e:
        # Handle all our custom Docker-related errors
        error_type = type(e).__name__
        logger.exception(f"{error_type} occurred during code execution.")
        reply_msg = str(e) # Use the message from the raised exception
        save_temp_config(
            tool_use={
                "name": f"Execute Code ({error_type})",
                "input": code_string,
                "output": reply_msg,
            },
        )
        reply(reply_msg)
        return reply_msg # Return the error message

    except Exception as e:
        # Catch any other unexpected errors
        logger.exception("An unexpected error happened in execute_code.")
        reply_msg = f"An unexpected error occurred: {e}"
        save_temp_config(
            tool_use={
                "name": "Execute Code (Unexpected Error)",
                "input": code_string,
                "output": reply_msg,
            },
        )
        reply(reply_msg)
        return reply_msg
