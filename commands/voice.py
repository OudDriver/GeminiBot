from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

import discord
from discord.ext import commands, voice_recv
from google.genai.types import (
    Content,
    LiveConnectConfig,
    Modality,
    Part,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)

# Assuming live now returns the process_audio_task
from packages.audio import AudioSink, AudioSource, live
from packages.utilities.file_utils import read_temp_config

if TYPE_CHECKING:
    from google.genai import Client

# --- Global State ---
voice_client: voice_recv.VoiceRecvClient | None = None
audio_sink: AudioSink | None = None
audio_queue: asyncio.Queue | None = None
live_task: asyncio.Task | None = None

logger = logging.getLogger(__name__)

# --- State Management ---

def _reset_state() -> None:
    """Resets the global voice state variables to None."""
    global voice_client, audio_sink, audio_queue, live_task
    voice_client = None
    audio_sink = None
    audio_queue = None
    live_task = None
    logger.info("Global voice state reset.")


async def _disconnect_from_voice_channel(
        vc: voice_recv.VoiceRecvClient,
        channel_name: str,
) -> None:
    if vc.is_listening():
        vc.stop_listening()
        logger.info("Stopped listening.")
    if vc.is_playing():
        vc.stop()
        logger.info("Stopped playing.")
    if vc.is_connected():
        await vc.disconnect(force=True)
        logger.info(f"Disconnected from voice channel {channel_name}.")


def _clear_queue(queue: asyncio.Queue) -> None:
    while not queue.empty():
        queue.get_nowait()


async def _cleanup_voice_state(error_context: str = "cleanup") -> None:
    """Safely cleans up voice client, tasks, and resets state."""
    logger.info(f"Starting cleanup due to: {error_context}")

    if live_task and not live_task.done():
        logger.info("Cancelling Gemini Live task.")
        try:
            live_task.cancel()
            await asyncio.wait_for(live_task, timeout=1.0)
        except asyncio.CancelledError:
            logger.info("Gemini Live task successfully cancelled.")
        except asyncio.TimeoutError:
            logger.warning("Gemini Live task did not cancel within timeout.")
        except Exception:
            logger.exception("Exception during live_task cancellation wait.")

    if voice_client:
        channel_name = (
            voice_client.channel.name
            if voice_client.channel
            else "Unknown Channel"
        )
        try:
            await _disconnect_from_voice_channel(voice_client, channel_name)
        except Exception:
            logger.exception("Error during Discord voice client cleanup.")

    if audio_queue:
        try:
            _clear_queue(audio_queue)
        except asyncio.QueueEmpty:
            logger.info("audio_queue is now empty.")
        except Exception:
            logger.exception("Error clearing audio queue.")
    _reset_state()
    logger.info("Voice state cleanup finished.")


def _generate_config(system_instructions: str, voice_name: str) -> LiveConnectConfig:
    """Generates a config for Gemini Multimodal Live API."""
    # (This function was already well-defined)
    return LiveConnectConfig(
        response_modalities=[Modality.AUDIO],
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice_name),
            ),
        ),
        system_instruction=Content(
            parts=[Part.from_text(text=system_instructions)],
            role="user",
        ),
    )

def _load_system_config() -> tuple[str, str]:
    """Loads configuration from the temporary file."""
    # Consider making voice name configurable too
    default_voice_name = "Leda"
    try:
        temp_config = read_temp_config()
        system_instructions = temp_config["system_prompt"]
        voice_name = temp_config.get("voice_name", default_voice_name) # Example
        return system_instructions, voice_name
    except FileNotFoundError:
        logger.exception("Configuration file temp/temp_config.json not found.")
        raise  # Re-raise to be caught by the command handler
    except KeyError as e:
         logger.exception("Missing key in temp_config.json.")
         msg = f"Missing key {e} in configuration."
         raise FileNotFoundError(msg) from e
    except Exception as e:
        logger.exception("Failed to load or parse temp_config.json.")
        msg = "Failed to read or parse configuration."
        raise FileNotFoundError(msg) from e


async def _initialize_audio_components() -> None:
    """Initializes the audio queue and sink."""
    global audio_queue, audio_sink
    audio_queue = asyncio.Queue()
    audio_sink = AudioSink(audio_queue)
    logger.debug("Audio queue and sink initialized.")
    if not audio_queue or not audio_sink:
        msg = "audio_queue or audio_sink not initialized."
        raise RuntimeError(msg)

async def _connect_to_voice_channel(
        channel: discord.VoiceChannel,
) -> voice_recv.VoiceRecvClient:
    """Connects to the specified voice channel."""
    global voice_client
    try:
        vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
        voice_client = vc # Update global state *after* successful connection
        logger.info(f"Connected to voice channel {channel.name}")
        return vc
    except discord.ClientException:
        logger.exception("Already connected or failed to connect.")
        raise
    except Exception:
        logger.exception(f"Unexpected error connecting to voice channel {channel.name}")
        raise

def _start_discord_audio_io(vc: voice_recv.VoiceRecvClient, sink: AudioSink) -> None:
    """Starts listening for audio and sets up playback."""
    audio_source = AudioSource()
    vc.listen(sink)
    vc.play(audio_source)
    logger.info("Started listening and playing audio.")

async def _start_gemini_live_task(
        queue: asyncio.Queue,
        client: Client,
        model: str,
        config: LiveConnectConfig,
) -> None:
    """Creates and starts the background task for Gemini Live."""
    global live_task
    global live_task
    if not queue:
        logger.error("Cannot start Gemini task: Audio queue is not initialized.")
        msg = "Audio queue is not initialized."
        raise ValueError(msg)
    try:
        live_task = asyncio.create_task(
            live(queue, client, model, config),
            name="GeminiLiveTask",
        )
        def handle_live_task_exception(task):
            if task.cancelled():
                logger.info("Gemini Live task was cancelled.")
                return
            if task.exception():
                logger.error("Gemini Live task failed with an unhandled exception:", exc_info=task.exception())
        live_task.add_done_callback(handle_live_task_exception)

        logger.info(f"Gemini Live task created for model {model}.")

    except Exception:
        logger.exception("Failed to create Gemini Live task.")
        raise # Re-raise

def voice(genai_client: Client) -> Callable:
    """Factory function to create the /voice command."""

    @commands.hybrid_command(name="voice")
    async def command(ctx: commands.Context) -> None:
        """Joins your voice channel and starts the Gemini Live session."""
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command.")
            return
        if voice_client is not None:
            await ctx.send("I'm already in a voice channel. Use `/leave` first.")
            return

        channel = ctx.author.voice.channel

        try:
            try:
                await _initialize_audio_components()
            except RuntimeError:
                logger.exception(
                    "An unexpected RuntimeError happened during initializing "
                    "audio components!",
                )

            model = "gemini-2.0-flash-live-001"
            vc = await _connect_to_voice_channel(channel) # Sets global voice_client

            system_instructions, voice_name = _load_system_config()
            gemini_config = _generate_config(system_instructions, voice_name)

            await _start_gemini_live_task(
                audio_queue,
                genai_client,
                model,
                gemini_config,
            )

            _start_discord_audio_io(vc, audio_sink)

            logger.info(
                f"Successfully joined {channel.name} "
                f"and started Gemini Live session.",
            )
            await ctx.send(f"Joined **{channel.name}**! Ready when you are.")

        except FileNotFoundError as e:
            logger.exception("Configuration error")
            await ctx.send(f"Configuration error: {e}. Cannot start voice session.")
            await _cleanup_voice_state("config_error") # Use the central cleanup
        except discord.ClientException:
            # This might occur
            # if status changes between the initial check and connect attempt
            logger.exception("Discord client exception during join.")
            await ctx.send(
                "There was an issue connecting to the voice channel. "
                "Am I already in one?",
            )
            # No state should have been significantly changed, reset just in case
            _reset_state()
        except Exception:
            logger.exception(
                "An unexpected error occurred during the voice join process.",
            )
            await ctx.send(
                "An unexpected error occurred while trying to join the voice channel.",
            )
            # Use the robust cleanup function
            await _cleanup_voice_state("join_exception")

    return command

@commands.hybrid_command()
async def leave(ctx: commands.Context) -> None:
    """Leaves the current voice channel and cleans up resources."""
    if voice_client is None:
        await ctx.send("I'm not currently in a voice channel.")
        return

    channel_name = (
        voice_client.channel.name
        if voice_client and voice_client.channel else "Unknown Channel"
    )
    logger.info(f"Leave command invoked for channel {channel_name}.")

    try:
        await _cleanup_voice_state("leave_command") # Use the central cleanup function
        await ctx.send(f"Left **{channel_name}**.")
    except Exception:
        # Catch potential errors during cleanup itself,
        # though _cleanup_voice_state handles internal exceptions
        logger.exception("Error during execution of leave command's cleanup.")
        await ctx.send(
            "An error occurred while trying to leave. State might be inconsistent.",
        )
        # Attempt to reset state anyway
        _reset_state()
