import time
import random
import string
import sys
import io
import logging

def generateUniqueFileName(extension):
    """
    Generates a unique filename using the current timestamp and a random string.
    """
    timestamp = int(time.time()) 
    randomStr = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{randomStr}.{extension}"

async def sendLongMessage(ctx, message, length):
    """Sends a long message in chunks."""
    for i in range(0, len(message), length):
        await ctx.reply(message[i:i + length])

def execute_code(code_string: str):
    """Executes Python code from a string and captures the output.

    Args:
        code_string: The string containing the Python code to execute.
        global_namespace: Optional dictionary to use as the global namespace.

    Returns:
        The standard output (stdout) captured during code execution.
    """

    cstring = code_string.encode().decode('unicode_escape')
    
    logging.info('\n' + cstring)

    # Redirect stdout and stderr to capture output
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = captured_stdout = io.StringIO()
    sys.stderr = captured_stderr = io.StringIO()

    # Use provided global_namespace or create a new one
    global_namespace = {}
    try:
        # Execute the code in the custom global namespace
        exec(cstring, global_namespace)
    except Exception as e:
        # Capture the error message
        captured_stderr.write(f"Error during code execution: {e}") 
        logging.info(captured_stderr.getvalue())
        return captured_stderr.getvalue()
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return captured_stdout.getvalue()
