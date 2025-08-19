from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

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

from packages.audio import AudioSink, AudioSource, live
from packages.utilities.file_utils import read_temp_config

if TYPE_CHECKING:
    from google.genai import Client
    from main import GeminiBot

logger = logging.getLogger(__name__)


class VoiceCog(commands.Cog, name="Voice"):
    """A cog for managing Discord voice channel integration with Gemini Live."""

    def __init__(self, bot: "GeminiBot", genai_client: Client):
        self.bot = bot
        self.genai_client = genai_client
        self.voice_client: voice_recv.VoiceRecvClient | None = None
        self.audio_sink: AudioSink | None = None
        self.audio_queue: asyncio.Queue | None = None
        self.live_task: asyncio.Task | None = None

    def _reset_state(self) -> None:
        """Resets the cog's voice state variables to None."""
        self.voice_client = None
        self.audio_sink = None
        self.audio_queue = None
        self.live_task = None
        logger.info("Voice cog state reset.")

    async def _disconnect_from_voice_channel(self, vc: voice_recv.VoiceRecvClient) -> None:
        """Disconnects from the given voice client."""
        channel_name = vc.channel.name if vc.channel else "Unknown Channel"
        if vc.is_listening():
            vc.stop_listening()
            logger.info("Stopped listening.")
        if vc.is_playing():
            vc.stop()
            logger.info("Stopped playing.")
        if vc.is_connected():
            await vc.disconnect(force=True)
            logger.info(f"Disconnected from voice channel {channel_name}.")

    def _clear_queue(self, queue: asyncio.Queue) -> None:
        """Clears all items from the given queue."""
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass # Should not happen given the while condition
        logger.debug("Audio queue cleared.")


    async def _cleanup_voice_state(self, error_context: str = "cleanup") -> None:
        """Safely cleans up voice client, tasks, and resets state."""
        logger.info(f"Starting cleanup due to: {error_context}")

        if self.live_task and not self.live_task.done():
            logger.info("Cancelling Gemini Live task.")
            try:
                self.live_task.cancel()
                await asyncio.wait_for(self.live_task, timeout=1.0)
            except asyncio.CancelledError:
                logger.info("Gemini Live task successfully cancelled.")
            except asyncio.TimeoutError:
                logger.warning("Gemini Live task did not cancel within timeout.")
            except Exception:
                logger.exception("Exception during live_task cancellation wait.")

        if self.voice_client:
            try:
                await self._disconnect_from_voice_channel(self.voice_client)
            except Exception:
                logger.exception("Error during Discord voice client cleanup.")

        if self.audio_queue:
            try:
                self._clear_queue(self.audio_queue)
            except Exception:
                logger.exception("Error clearing audio queue.")
        self._reset_state()
        logger.info("Voice state cleanup finished.")


    def _generate_config(self, system_instructions: str, voice_name: str) -> LiveConnectConfig:
        """Generates a config for Gemini Multimodal Live API."""
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

    def _load_system_config(self) -> tuple[str, str]:
        """Loads configuration from the temporary file."""
        default_voice_name = "Leda"
        try:
            temp_config = read_temp_config()
            system_instructions = temp_config["system_prompt_data"] # Corrected key
            voice_name = temp_config.get("voice_name", default_voice_name)
            return system_instructions, voice_name
        except FileNotFoundError:
            logger.exception("Configuration file temp/temp_config.json not found.")
            raise
        except KeyError as e:
            logger.exception(f"Missing key {e} in temp_config.json.")
            msg = f"Missing key {e} in configuration."
            raise FileNotFoundError(msg) from e
        except Exception as e:
            logger.exception("Failed to load or parse temp_config.json.")
            msg = "Failed to read or parse configuration."
            raise FileNotFoundError(msg) from e


    async def _initialize_audio_components(self) -> None:
        """Initializes the audio queue and sink."""
        self.audio_queue = asyncio.Queue()
        self.audio_sink = AudioSink(self.audio_queue)
        logger.debug("Audio queue and sink initialized.")
        if not self.audio_queue or not self.audio_sink:
            msg = "audio_queue or audio_sink not initialized."
            raise RuntimeError(msg)

    async def _connect_to_voice_channel(self, channel: discord.VoiceChannel) -> voice_recv.VoiceRecvClient:
        """Connects to the specified voice channel."""
        try:
            vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
            self.voice_client = vc # Update cog state *after* successful connection
            logger.info(f"Connected to voice channel {channel.name}")
            return vc
        except discord.ClientException:
            logger.exception("Already connected or failed to connect.")
            raise
        except Exception:
            logger.exception(f"Unexpected error connecting to voice channel {channel.name}")
            raise

    def _start_discord_audio_io(self, vc: voice_recv.VoiceRecvClient, sink: AudioSink) -> None:
        """Starts listening for audio and sets up playback."""
        audio_source = AudioSource()
        vc.listen(sink)
        vc.play(audio_source)
        logger.info("Started listening and playing audio.")

    async def _start_gemini_live_task(
            self,
            queue: asyncio.Queue,
            model: str,
            config: LiveConnectConfig,
    ) -> None:
        """Creates and starts the background task for Gemini Live."""
        if not queue:
            logger.error("Cannot start Gemini task: Audio queue is not initialized.")
            msg = "Audio queue is not initialized."
            raise ValueError(msg)
        try:
            self.live_task = asyncio.create_task(
                live(queue, self.genai_client, model, config),
                name="GeminiLiveTask",
            )
            def handle_live_task_exception(task):
                if task.cancelled():
                    logger.info("Gemini Live task was cancelled.")
                    return
                if task.exception():
                    logger.error(
                        "Gemini Live task failed with an unhandled exception:",
                        exc_info=task.exception()
                    )
            self.live_task.add_done_callback(handle_live_task_exception)

            logger.info(f"Gemini Live task created for model {model}.")

        except Exception:
            logger.exception("Failed to create Gemini Live task.")
            raise # Re-raise

    @commands.hybrid_command(name="voice")
    async def voice_command(self, ctx: commands.Context) -> None:
        """Joins your voice channel and starts the Gemini Live session."""
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command.")
            return
        if self.voice_client is not None:
            await ctx.send("I'm already in a voice channel. Use `/leave` first.")
            return

        channel = ctx.author.voice.channel

        try:
            await self._initialize_audio_components()
            if not self.audio_queue or not self.audio_sink: # Double check after initialization
                raise RuntimeError("Audio components failed to initialize.")

            model = "gemini-2.0-flash-live-001" # This model is hardcoded, consider making it configurable
            vc = await self._connect_to_voice_channel(channel)

            system_instructions, voice_name = self._load_system_config()
            gemini_config = self._generate_config(system_instructions, voice_name)

            await self._start_gemini_live_task(
                self.audio_queue,
                model,
                gemini_config,
            )

            self._start_discord_audio_io(vc, self.audio_sink)

            logger.info(
                f"Successfully joined {channel.name} "
                f"and started Gemini Live session.",
            )
            await ctx.send(f"Joined **{channel.name}**! Ready when you are.")

        except FileNotFoundError as e:
            logger.exception("Configuration error")
            await ctx.send(f"Configuration error: {e}. Cannot start voice session.")
            await self._cleanup_voice_state("config_error")
        except discord.ClientException:
            logger.exception("Discord client exception during join.")
            await ctx.send(
                "There was an issue connecting to the voice channel. "
                "Am I already in one?",
            )
            self._reset_state() # Reset state as connection failed
        except Exception:
            logger.exception(
                "An unexpected error occurred during the voice join process.",
            )
            await ctx.send(
                "An unexpected error occurred while trying to join the voice channel.",
            )
            await self._cleanup_voice_state("join_exception")

    @commands.hybrid_command(name="leave")
    async def leave_command(self, ctx: commands.Context) -> None:
        """Leaves the current voice channel and cleans up resources."""
        if self.voice_client is None:
            await ctx.send("I'm not currently in a voice channel.")
            return

        channel_name = (
            self.voice_client.channel.name
            if self.voice_client and self.voice_client.channel else "Unknown Channel"
        )
        logger.info(f"Leave command invoked for channel {channel_name}.")

        try:
            await self._cleanup_voice_state("leave_command")
            await ctx.send(f"Left **{channel_name}**.")
        except Exception:
            logger.exception("Error during execution of leave command's cleanup.")
            await ctx.send(
                "An error occurred while trying to leave. State might be inconsistent.",
            )
            self._reset_state() # Attempt to reset state anyway

async def setup(bot: "GeminiBot"):
    """Adds the VoiceCog to the bot."""
    await bot.add_cog(VoiceCog(bot, bot.genai_client))