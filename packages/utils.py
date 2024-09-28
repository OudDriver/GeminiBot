import time
import random
import string
import discord
import asyncio
import logging
import sys
import io
import nest_asyncio

nest_asyncio.apply()

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
        
def timeout(member_id: int, duration: int= 60, reason: str = None):
    """Timeouts a Discord member using their ID for a specified duration.

        Args:
            member_id: The user's ID.
            duration: Duration in seconds. Default is 60 seconds.
            reason: The reason why the user is timed out.
    """
    async def _mute(member_id: int, duration: int, reason: str = None):
        if duration <= 0:
            return "Time must be a positive integer"
        
        from commands.prompt import ctxGlob
        
        guild = ctxGlob.guild
        try:
            member = guild.get_member(member_id)
            if member is None:
                await ctxGlob.send("Member not found in this server.")
                return

            await member.timeout(discord.utils.utcnow() + discord.utils.compute_timedelta(seconds=duration), reason=reason)
            await ctxGlob.send(f"Member with ID {member_id} has been timed out for {duration} seconds. Reason: {reason}")
            return f"Succesful! Member with ID {member_id} has been timed out for {duration} seconds. Reason: {reason}"
        except discord.Forbidden:
            return "Missing Permissions. Ping <@578997249741160467> to fix."
        except discord.HTTPException as e:
            return f"Something Happened. {e}"
        
    try:
        loop = asyncio.get_running_loop() 
        return loop.run_until_complete(_mute(member_id, duration, reason))
    except RuntimeError:  # No event loop running
        return asyncio.run(_mute(member_id, duration, reason))

def send(msg):
    async def _send(msg):
        from commands.prompt import ctxGlob
        await ctxGlob.send(msg)
        
    try:
        loop = asyncio.get_running_loop() 
        return loop.run_until_complete(_send(msg))
    except Exception as e:
        logging.error(e)
    
def reply(msg):
    async def _reply(msg):
        from commands.prompt import ctxGlob
        await ctxGlob.reply(msg)
    
    try:
        loop = asyncio.get_running_loop() 
        return loop.run_until_complete(_reply(msg))
    except Exception as e:
        logging.error(e)
    
def hi():
    """
    Just says hi! Do whatever you want with this function! (Well, it is actually just a test function)
    """
    async def _hi():
        await send("SassBot Said Hi!")
        return ":D"
        
    try:
        loop = asyncio.get_running_loop() 
        return loop.run_until_complete(_hi())
    except RuntimeError:  # No event loop running
        return asyncio.run(_hi())
    
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
        final = f"Code:\n```py\n{cstring}\n```\nError:`{captured_stderr.getvalue()}`"
        reply(final)
        return captured_stderr.getvalue()
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    final = f"Code:\n```py\n{cstring}\n```\nOutput:\n```\n{captured_stdout.getvalue()}\n```"
    reply(final)
    return captured_stdout.getvalue()
