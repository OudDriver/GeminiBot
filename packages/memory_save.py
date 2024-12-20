import logging


def save_memory(msg: str):
    """
    Saves a memory into a file

    Args:
        msg: The message to save
    """

    logging.info(f"Saved {msg}")

    with open("memory.txt", "a") as f:
        f.write('\n' + msg)

def load_memory():
    """
    Loads a memory from a file

    Returns:
        The loaded memory
    """
    try:
        with open("memory.txt", "r") as f:
            mem = f.read()
            logging.info(f"Loaded {mem}")
            return mem
    except FileNotFoundError:
        return ""