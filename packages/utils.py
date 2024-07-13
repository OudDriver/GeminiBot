import time
import random
import string
import re

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
        await ctx.send(message[i:i + length])
        
def makeOutputWithCodeExecutionCleaner(text: str):
    if re.search(r"``` (.*)\n([\s\S]+.*)```", text):
        badSnippetText = re.search(r"``` (.*)\n([\s\S]+.*)```", text).group(0)
        outputSnippet = re.search(r"```\n([^\n```][\s\S]+.*)```", badSnippetText).group(0)
        outputSnippetOnly = re.sub(r"(```|\n)", '', outputSnippet)
        codeSnippet = re.sub(outputSnippet, '', badSnippetText)
        codeSnippetOnly = re.sub(r"(``` (.*)|\n```)", '', codeSnippet)
        language = re.sub(r'``` ', '', re.search(r"``` (.*)", badSnippetText).group(0))
        others = re.sub(r"``` (.*)\n([\s\S]+.*)```", '', text)
        output = f"""```{language}
{codeSnippetOnly}
```
```
Output: {outputSnippetOnly}
```
{others}"""
        return output
    else:
        return text
    

