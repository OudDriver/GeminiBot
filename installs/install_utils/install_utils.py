from __future__ import annotations

import contextlib
import logging
import os
import platform
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import IO
from urllib.parse import urlparse

import requests
from tqdm import tqdm


def setup_logging() -> None:
    """Configure logging to file and console."""
    # Define log format
    log_format = (
        "%(asctime)s - "
        "%(levelname)s - "
        "%(name)s - "
        "%(filename)s:%(lineno)d - "
        "%(message)s"
    )
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    folder = Path("logs")
    file = folder / Path("installation.log")

    folder.mkdir(parents=True, exist_ok=True)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

setup_logging()
logger = logging.getLogger(__name__)

def has_admin() -> bool:
    """Check if current user is an administrator.

    Returns:
        A boolean that indicates if the current user is an administrator.

    """
    if os.name == "nt":
        try:
            # Attempt a privileged operation (listing SystemRoot/temp)
            list((Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "temp").iterdir())
        except (PermissionError, OSError): # Added OSError for broader checks
            return False
        else:
            return True
    # Check for root privileges on Unix-like systems (e.g., via sudo)
    # os.geteuid() == 0 is the most reliable check for root
    return os.geteuid() == 0


def _prepare_command_list(
    cmd_input: str | list[str], # Use Union for clarity
    admin: bool,
) -> list[str] | None: # Return Optional[List[str]] to signal failure
    """Prepare the command list for execution.

    Handles string-to-list conversion and prepends 'sudo' if admin rights
    are requested, necessary, and possible.

    Args:
        cmd_input: The command as a string or list of strings.
        admin: Whether admin privileges are requested.

    Returns:
        The prepared command list, or None if admin rights are needed
        but 'sudo' is unavailable.

    """
    if isinstance(cmd_input, str):
        cmd_list = cmd_input.split()
        if not cmd_list: # Handle empty string case
             logger.error("Error: Received empty command string.")
             return None
    elif isinstance(cmd_input, list):
        cmd_list = list(cmd_input) # Create a copy
        if not cmd_list: # Handle empty list case
             logger.error("Error: Received empty command list.")
             return None
    else:
        logger.error(f"Error: Invalid command type: {type(cmd_input)}. "
                     f"Expected str or list.")
        return None

    # Check if the command already starts with sudo
    starts_with_sudo = cmd_list[0] == "sudo"

    # If admin is requested, we are *not* currently admin
    if admin and not has_admin() and not starts_with_sudo:
        sudo_path = shutil.which("sudo")
        if sudo_path:
            cmd_list.insert(0, "sudo")
            logger.debug("Prepending 'sudo' to command.")
        else:
            logger.error("Error: Admin privileges required, but running as non-admin "
                         "and 'sudo' command not found.")
            logger.error("Please run this script as root/admin or install sudo.")
            return None

    return cmd_list


def _stream_reader(
    stream: IO[str] | None,
    output_queue: queue.Queue,
    label: str,
    suppress_output: bool,
) -> None:
    """Read lines from a subprocess text stream and puts them into a queue.

    See original docstring for details.
    """
    if stream is None or suppress_output:
        output_queue.put((label, None))
        return

    sentinel = ""
    try:
        # Read until EOF (readline returns empty string)
        for line in iter(stream.readline, sentinel):
             if not line and stream.closed: # Handle unexpected stream closure
                 logger.debug(f"Stream {label} detected as closed during iteration.")
                 break
             output_queue.put((label, line)) # Put the read line in the queue

        if not stream.closed:
            logger.debug(
                f"Stream {label} iteration finished, "
                f"but stream not marked closed yet.",
            )

    except ValueError:
        logger.debug(f"Stream {label} closed unexpectedly (ValueError).")
    except Exception:
        logger.exception(f"Error reading {label} stream.")
        with contextlib.suppress(Exception):
            output_queue.put((label, f"ERROR reading stream {label}\n"))
    finally:
        output_queue.put((label, None))
        with contextlib.suppress(Exception):
            if stream and not stream.closed:
                stream.close()
        logger.debug(f"Stream reader for {label} finished and put sentinel.")


# --- Function 2: Start the Subprocess ---
def _start_subprocess(
    cmd_list: list[str], cwd: str | Path | None = None
) -> subprocess.Popen | None:
    """Starts the subprocess and handles immediate errors."""
    try:
        log_message = f"Running command: {' '.join(cmd_list)}"
        if cwd:
            log_message += f" in directory: {cwd}"
        logger.info(log_message)

        return subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd, # Add the cwd argument here
        )
    except FileNotFoundError:
        # Check if the CWD is the issue vs. the command itself
        if cwd and not Path(cwd).is_dir():
            logger.exception(f"Working directory not found: {cwd}")
        else:
            logger.exception(f"Command not found: {cmd_list[0]}")
        return None
    except Exception:
        # Catch other potential Popen errors (permissions, etc.)
        logger.exception(
            f"Failed to start subprocess for command: {' '.join(cmd_list)}",
        )
        return None

# --- Function 3: Set up and Start Stream Reader Threads ---
def _start_stream_readers(
    process: subprocess.Popen,
    suppress_output: bool,
) -> tuple[queue.Queue, threading.Thread, threading.Thread]:
    """Creates queue and starts threads for reading stdout/stderr."""
    output_queue = queue.Queue()

    stdout_thread = threading.Thread(
        target=_stream_reader,
        args=(process.stdout, output_queue, "STDOUT", suppress_output),
        daemon=True, # Daemon threads exit when the main program exits
    )
    stderr_thread = threading.Thread(
        target=_stream_reader,
        args=(process.stderr, output_queue, "STDERR", suppress_output),
        daemon=True,
    )

    stdout_thread.start()
    stderr_thread.start()
    logger.debug("Stdout and Stderr stream reader threads started.")

    return output_queue, stdout_thread, stderr_thread

def _process_output_queue(
    output_queue: queue.Queue,
    process: subprocess.Popen,
    num_streams: int = 2,
) -> None:
    """Reads lines from the queue and prints them until all streams are done."""
    streams_finished = 0
    while streams_finished < num_streams:
        try:
            label, line = output_queue.get(timeout=0.1)

            if line is None:
                streams_finished += 1
                logger.debug(
                    f"Received sentinel for {label}. "
                    f"Finished streams: {streams_finished}/{num_streams}",
                )
                continue

            if label == "STDOUT":
                sys.stdout.write(line)
                sys.stdout.flush()
            elif label == "STDERR":
                sys.stderr.write(line)
                sys.stderr.flush()

        except queue.Empty:
            if process.poll() is not None and streams_finished < num_streams:
                logger.debug(
                    "Queue empty, process terminated, waiting for final sentinels.",
                )
            continue

    logger.debug("All stream sentinels received. Exiting queue processing loop.")


def _wait_for_completion(
    process: subprocess.Popen,
    stdout_thread: threading.Thread,
    stderr_thread: threading.Thread,
    timeout: float = 1.0,
) -> int:
    """Joins reader threads and waits for the subprocess to exit."""
    stdout_thread.join(timeout=timeout)
    stderr_thread.join(timeout=timeout)

    if stdout_thread.is_alive():
        logger.warning("Stdout reader thread did not finish within timeout.")
    if stderr_thread.is_alive():
        logger.warning("Stderr reader thread did not finish within timeout.")

    logger.debug("Waiting for subprocess to terminate...")
    exit_code = process.wait()
    logger.debug(f"Subprocess terminated with exit code: {exit_code}")
    return exit_code

def _ensure_process_terminated(process: subprocess.Popen, context: str) -> None:
    """Attempts to terminate/kill a process if it's still running."""
    if process and process.poll() is None:
        logger.warning(f"Process still running in {context}. Attempting termination.")
        process.terminate()
        try:
            process.wait(timeout=2)
            logger.info("Process terminated gracefully.")
        except subprocess.TimeoutExpired:
            logger.warning("Process did not terminate gracefully after 2s, killing.")
            process.kill()
            process.wait()
            logger.info("Process killed.")

def _execute_and_stream_output(
    cmd_list: list[str],
    suppress_output: bool = False,
    cwd: str | Path | None = None,
) -> int | None:
    """Executes a command, streams its stdout/stderr, and waits for completion.

    Args:
        cmd_list: The command and arguments as a list of strings.
        suppress_output: If True, stdout/stderr from the command are not printed.
        cwd: The working directory for the command. If None, uses the
             current working directory.

    Returns:
        The exit code of the command (int), or None if the process
        could not be started or an unexpected error occurred.
    """
    process: subprocess.Popen | None = None

    try:
        process = _start_subprocess(cmd_list, cwd)
        if process is None:
            return None

        if process.stdout is None:
            msg = "Process stdout stream is None"
            raise RuntimeError(msg)
        if process.stderr is None:
            msg = "Process stderr stream is None"
            raise RuntimeError(msg)

        output_queue, stdout_thread, stderr_thread = _start_stream_readers(
            process, suppress_output,
        )

        _process_output_queue(output_queue, process)

        return _wait_for_completion(process, stdout_thread, stderr_thread)

    except Exception:
        logger.exception("An unexpected error occurred during command execution.")
        if process:
            _ensure_process_terminated(process, "unexpected exception handler")
        return None

    finally:
        if process:
             _ensure_process_terminated(process, "finally block")

def run_command(
        cmd_input: str | list[str],
        admin: bool = True,
        suppress_output: bool = False,
        cwd: str | Path | None = None,
) -> bool:
    """Run a command, stream its output in real-time, and handle admin privileges.

    Prepends 'sudo' if `admin=True` is specified, the script is not already
    running as root/admin, and the 'sudo' command is available.

    Prints the command's stdout and stderr to the console as they arrive.

    Args:
        cmd_input: The command to run, as a single string or a list of strings.
        admin: If True, attempt to run the command with admin/root privileges
               using 'sudo' if necessary.
        suppress_output: Whether to supress output or not
        cwd: The working directory for the command. If None, uses the
             current working directory of the script.

    Returns:
        True if the command executed successfully (exit code 0), False otherwise
        (non-zero exit code, command not found, sudo error, or other exception).

    """
    if platform.system() == "Windows":
        admin = False
    final_cmd_list = _prepare_command_list(cmd_input, admin)

    if final_cmd_list is None:
        # Preparation failed (e.g., sudo needed but unavailable, invalid input)
        return False

    try:
        exit_code = _execute_and_stream_output(
            final_cmd_list, suppress_output, cwd
        )

        if exit_code is None:
            # Execution failed to start or encountered a major error
             logger.error(f"Command execution failed for: {' '.join(final_cmd_list)}")
             return False
        if exit_code == 0:
            logger.info(f"Command successful: {' '.join(final_cmd_list)} "
                        f"(Exit Code: 0)")
            return True
        logger.warning(
            f"Command failed: {' '.join(final_cmd_list)} (Exit Code: {exit_code})",
        )

    except Exception:
        # Catch any truly unexpected errors during the orchestration
        logger.exception("An unexpected error occurred in run_command.")
        return False

    else:
        return False


def get_distro_info() -> dict[str, list | list[str] | None | str]:
    """Detect the Linux distribution information from /etc/os-release.

    Returns:
         a dictionary with 'ID' and 'ID_LIKE' (list).

    """
    distro_info = {"ID": None, "ID_LIKE": []}

    try:
        with open("/etc/os-release") as f:
            for lines in f:
                line = lines.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove potential quotes around value
                    value = value.strip('"\'')
                    if key == "ID":
                        # noinspection PyTypeChecker
                        distro_info["ID"] = value.lower()
                    elif key == "ID_LIKE":
                        # ID_LIKE can be a space-separated list
                        distro_info["ID_LIKE"] = [
                            item.lower() for item in value.split()
                        ]
    except FileNotFoundError:
        logger.exception("Error: /etc/os-release not found."
                         "Cannot determine distribution.")
    except Exception:
        logger.exception("Error reading /etc/os-release.")

    return distro_info


def download_file_with_progress(
    url: str,
    local_filename: str | None = None,
    chunk_size: int = 8192,
) -> None:
    """Download a file from a URL showing a progress bar.

    Args:
        url (str): The URL of the file to download.
        local_filename (str, optional): The local path to save the file.
                                         If None, derives filename from URL.
        chunk_size (int, optional): Size of download chunks in bytes. Defaults to 8192.

    """
    try:
        # If local_filename is not specified, derive it from the URL
        if local_filename is None:
            parsed_url = urlparse(url)
            local_filename = Path(parsed_url.path).name
            if not local_filename:  # Handle cases where path is empty or just '/'
                local_filename = "downloaded_file"
                logger.warning(
                    f"Could not derive filename from URL. "
                    f"Saving as '{local_filename}'.",
                )

        logger.info(f"Attempting to download '{url}' to '{local_filename}'...")

        # Send a GET request to the URL, streaming the response
        with requests.get(url, stream=True, timeout=30) as r:
            # Check if the request was successful
            r.raise_for_status()

            # Get the total file size from headers, if available
            total_size_in_bytes = int(r.headers.get("content-length", 0))

            # Warn if Content-Length header is missing
            if total_size_in_bytes == 0:
                logger.info(
                    "Warning: Content-Length header not found. "
                    "Progress bar may be inaccurate or infinite.",
                )

            # Open the local file in binary write mode
            with (
                open(local_filename, "wb") as f,
                tqdm(
                    total=total_size_in_bytes,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=local_filename,
                    ncols=100,
                    miniters=1,
                    ascii=True,
                ) as pbar,
            ):
                # Iterate over the response data in chunks
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive new chunks
                        # Write chunk to file
                        f.write(chunk)
                        # Update progress bar by the size of the chunk written
                        pbar.update(len(chunk))

        # Check if the downloaded file size matches the expected size (if known)
        if (
            total_size_in_bytes != 0
            and Path(local_filename).stat().st_size != total_size_in_bytes
        ):
            logger.error(
                f"Download incomplete. Expected {total_size_in_bytes} bytes, "
                f"got {Path(local_filename).stat().st_size} bytes.",
            )
        else:
            logger.info(f"Download complete: '{local_filename}'")

    except requests.exceptions.RequestException:
        logger.exception("Error during download.")
    except OSError:
        logger.exception("Error writing file.")
    except Exception:
        logger.exception("An unexpected error occurred.")