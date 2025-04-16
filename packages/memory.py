import logging

from packages.utils import save_temp_config


def save_memory(msg: str):
    """
    Saves a memory. Use this as much as you need. E.g., when a user is telling a thing they like or a plan they are going to do.

    Args:
        msg: The message to save
    """

    logging.info(f"Saved {msg}")

    with open("memory.txt", "a") as f:
        f.write("\n" + msg)

    save_temp_config(
        tool_use={
            "name": "Search DuckDuckGo",
            "input": msg,
            "output": "",
        }
    )

def load_memory():
    """
    Loads a memory from a file

    Returns:
        The loaded memory
    """
    try:
        with open("memory.txt") as f:
            mem = f.read()
            logging.info(f"Loaded {mem}")
            return mem
    except FileNotFoundError:
        return ""