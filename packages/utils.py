from datetime import timedelta
import time
import random
import string
import discord
import asyncio
import logging
import sys
import io
import re
import nest_asyncio

from packages.maps import subscript_map, superscript_map

nest_asyncio.apply()

def generateUniqueFileName(extension):
    """
    Generates a unique filename using the current timestamp and a random string.
    """
    timestamp = int(time.time()) 
    randomStr = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{randomStr}.{extension}"

def clean_text(text: str):
    """
    Replaces <sub></sub> and <sup></sup> tags with their Unicode subscript and superscript equivalents.

    Args:
        text: The input string containing <sub></sub> and <sup></sup> tags.

    Returns:
        The string with the tags replaced by subscript and superscript characters.
    """
    def replace_sub(m):
        return ''.join(subscript_map.get(c, c) for c in m.group(1))

    def replace_sup(m):
         return ''.join(superscript_map.get(c, c) for c in m.group(1))

    text = re.sub(r'<sub>(.*?)</sub>', replace_sub, text)
    text = re.sub(r'<sup>(.*?)</sup>', replace_sup, text)
    
    matches = re.findall(r"\n<thought>[\s\S]*?<\/thought>\n", text)
    text = re.sub(r"\n<thought>[\s\S]*?<\/thought>\n", "", text)
    text = re.sub(r"\n<br>", "", text)
    
    return text, matches

async def sendLongMessage(ctx, message, length):
    """Sends a long message in chunks."""
    for i in range(0, len(message), length):
        await ctx.reply(message[i:i + length])
        
def timeout(member_id: int, duration: int= 60, reason: str = None):
    """Timeouts a Discord member using their ID for a specified duration. (It actually works)

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
            member = await guild.fetch_member(member_id)
            if member is None:
                await ctxGlob.send("Member not found in this server.")
                return

            await member.timeout(timedelta(seconds=duration), reason=reason)
            await ctxGlob.send(f"Member with ID {member_id} has been timed out for {duration} seconds. Reason: {reason}")
            return f"Succesful! Member with ID {member_id} has been timed out for {duration} seconds. Reason: {reason}"
        except discord.Forbidden:
            await ctxGlob.send("Missing Permission!")
            return "Missing Permissions. Ping <@578997249741160467> to fix."
        except discord.HTTPException as e:
            await ctxGlob.send(e)
            return f"Something Happened. {e}"
        
    loop = asyncio.get_running_loop() 
    return loop.run_until_complete(_mute(member_id, duration, reason))

def send(msg):
    async def _send(msg):
        from commands.prompt import ctxGlob
        await ctxGlob.send(msg)
        
    loop = asyncio.get_running_loop() 
    return loop.run_until_complete(_send(msg))
    
def reply(msg):
    async def _reply(msg):
        from commands.prompt import ctxGlob
        await ctxGlob.reply(msg)
    
    loop = asyncio.get_running_loop() 
    return loop.run_until_complete(_reply(msg))
    
def hi():
    """
    A test function that says hi.
    """
    async def _hi():
        await send("SassBot Said Hi!")
        return "Sassbot Said Hi"
       
    loop = asyncio.get_running_loop() 
    return loop.run_until_complete(_hi())
    
def execute_code(code_string: str):
    """Executes Python code from a string and captures the output.

    Args:
        code_string: The string containing the Python code to execute.
        global_namespace: Optional dictionary to use as the global namespace.

    Returns:
        The standard output or standard error captured during code execution
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
        final = f"Code:\n```py\n{cstring}\n```\nError:`{captured_stderr.getvalue()}`"
        
        logging.info(captured_stderr.getvalue())
        reply(final)
        
        return captured_stderr.getvalue()
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    final = f"Code:\n```py\n{cstring}\n```\nOutput:\n```\n{captured_stdout.getvalue()}\n```"
    reply(final)
    return captured_stdout.getvalue()

