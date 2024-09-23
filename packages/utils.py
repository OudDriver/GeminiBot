import time
import random
import string
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
        