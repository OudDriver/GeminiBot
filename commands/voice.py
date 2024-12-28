from discord.ext import commands, voice_recv
from packages.audio import live
from google.genai import Client
import discord
import asyncio

voice_client = None
audio_queue = None
audio_sink = None

class AudioSink(voice_recv.AudioSink):
    def __init__(self, audio_queue):
        self.audio_queue = audio_queue

    def write(self, user, data):
        pcm = data.pcm
        self.audio_queue.put_nowait(pcm)

    def wants_opus(self):
        return False

    def cleanup(self):
        return

def voice(genai_client: Client):
    @commands.hybrid_command(name="voice")
    async def command(ctx: commands.Context):
        """Joins the voice channel of the user who invoked the command."""
        global voice_client, audio_queue, audio_sink

        if ctx.author.voice is None:
            await ctx.send("You are not in a voice channel.")
            return

        channel = ctx.author.voice.channel

        try:
            voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
        except discord.ClientException:
            await ctx.send("I am already in a voice channel")
            return
        except Exception as e:
            print(f"Error connecting to voice channel: {e}")
            await ctx.send("Failed to join your voice channel.")
            return

        audio_queue = asyncio.Queue()
        audio_sink = AudioSink(audio_queue)
        voice_client.listen(audio_sink)
        asyncio.create_task(live(audio_queue, genai_client, 'gemini-2.0-flash-exp', {"response_modalities": ["TEXT"]}))

        await ctx.send(f"Joined **{channel.name}**!")

    return command

@commands.hybrid_command()
async def leave(ctx):
    global voice_client, audio_queue, audio_sink

    if voice_client is None:
        await ctx.send("I am not in a voice channel.")
        return

    try:
      await voice_client.disconnect()
    except Exception as e:
        print(f"Error disconnecting from voice channel: {e}")
        await ctx.send("Failed to leave the voice channel.")
        return
    finally:
      voice_client = None
      audio_queue = None
      audio_sink = None

    await ctx.send("Left the voice channel.")