import logging

from packages.utilities.file_utils import save_temp_config

logger = logging.getLogger(__name__)

def save_memory(msg: str) -> None:
    """Save a memory.

    Use this as much as you need.
    E.g., when a user is telling a thing they like or a plan they are going to do.

    Args:
        msg: The message to save

    """
    logger.info(f"Saved {msg}")

    with open("memory.txt", "a") as f:
        f.write("\n" + msg)

    save_temp_config(
        tool_call={
            "name": "Save Memory",
            "input": msg,
            "output": "",
        },
    )

def load_memory() -> str:
    """Load a memory from a file.

    Returns:
        The loaded memory

    """
    try:
        with open("memory.txt") as f:
            mem = f.read()
            logger.info(f"Loaded {mem}")
            return mem
    except FileNotFoundError:
        return ""
