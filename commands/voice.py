from discord.ext import commands, voice_recv
from packages.audio import live, AudioSink, AudioSource
from google.genai import Client
import discord
import asyncio

audio_sink = None
audio_queue = asyncio.Queue()

voice_client = None

def voice(genai_client: Client):
    @commands.hybrid_command(name="voice")
    async def command(ctx: commands.Context):
        """Joins the voice channel of the user who invoked the command."""
        global voice_client, audio_queue, audio_sink

        if ctx.author.voice is None:
            await ctx.send("You are not in a voice channel.")
            return

        try:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
            audio_sink = AudioSink(audio_queue)
            voice_client.listen(audio_sink)
            asyncio.create_task(
                live(audio_queue, genai_client, 'gemini-2.0-flash-exp', {"response_modalities": ["AUDIO"]}))

            audio_source = AudioSource()
            voice_client.play(audio_source)
            await ctx.send(f"Joined **{channel.name}**!")
        except discord.ClientException:
            await ctx.send("I am already in a voice channel")
            return
        except Exception as e:
            print(f"Error connecting to voice channel: {e}")
            await ctx.send("Failed to join your voice channel.")
            return

    return command

@commands.hybrid_command()
async def leave(ctx: commands.Context):
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