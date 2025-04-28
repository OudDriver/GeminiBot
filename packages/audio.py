from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import discord
import numpy as np
import samplerate
from discord import Member, User
from discord.ext import voice_recv
from samplerate import ConverterType, Resampler

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google import genai
    from google.genai.types import LiveConnectConfig

unsorted_queue = asyncio.Queue(maxsize=15)
sorted_queue = asyncio.Queue(maxsize=15)

logger = logging.getLogger(__name__)

INT16_MAX = 32767
SILENCE_BYTES = bytes(3840)

class AudioSink(voice_recv.AudioSink):
    """Set up an audio sink for receiving Discord audio."""

    def __init__(self, audio_queue: asyncio.Queue) -> None:
        """Set up an audio queue for the sink to use."""
        self.audio_queue = audio_queue

    def write(self, user: Member | User | None, data: voice_recv.VoiceData) -> None:  # noqa: ARG002
        """Detect the incoming audio and stores it."""
        pcm = data.pcm
        self.audio_queue.put_nowait(pcm)

    def wants_opus(self) -> bool:
        """Tell discord_ext_voice_recv whether to not handle opus data.

        Returns:
            False to indicate that I don't want to handle opus data.

        """
        return False

    def cleanup(self) -> None:
        """Tell discord_ext_voice_recv on what to do when it wants to clean up.

        Returns:
            None, as cleanup isn't needed.

        """
        return


class AudioSource(discord.PCMAudio):
    """Set up an audio source to output to user."""

    def __init__(self) -> None:
        """Set up an audio queue for the source to use."""
        self.stream = sorted_queue

    def read(self) -> bytes:
        """Read from an arbitrary source.

        Returns:
            bytes of pcm audio data.

        """
        try:
            return self.stream.get_nowait()
        except asyncio.QueueEmpty:
            return SILENCE_BYTES
        except Exception:
            logger.exception("An unexpected error happened "
                             "when trying to read from a source.")
            return SILENCE_BYTES

    def is_opus(self) -> bool:
        """Tell Discord whether to not handle opus data.

        Returns:
            False to indicate that I don't want to handle opus data.

        """
        return False


def resample_to_gemini(data: bytes, source_rate: int, target_rate: int) -> bytes:
    """Resamples Discord PCM audio to Gemini PCM audio.

    Converts 48kHz 32-bit Discord PCM audio to 16kHz 16-bit Gemini PCM audio.

    Args:
        data: The input PCM audio data as bytes.
        source_rate: The sample rate of the input audio (e.g., 48000).
        target_rate: The desired sample rate for the output audio (e.g., 16000).

    Returns:
        The resampled PCM audio data as bytes.

    """
    if not data:
        return SILENCE_BYTES
    if source_rate == target_rate:
        data_np = np.frombuffer(data, dtype=np.int32)
        rescaled_data = (data_np // (2**16)).astype(np.int16)
        return rescaled_data.tobytes()

    try:
        data_np_int32 = np.frombuffer(data, dtype=np.int32)
        data_np_float64 = data_np_int32.astype(np.float64) / (2**31)

        ratio = target_rate / source_rate
        resampled_data_float = samplerate.resample(
            data_np_float64,
            ratio,
            "sinc_medium",
        )
        resampled_data_int16 = (resampled_data_float * INT16_MAX).astype(np.int16)

        return resampled_data_int16.tobytes()

    except samplerate.ResamplingError:
        logger.exception(f"Samplerate error during Gemini resampling.\n"
                         f"Input data length: {len(data)}")
        return SILENCE_BYTES

    except Exception:
        logger.exception("Unexpected error in resample_to_gemini.")
        return SILENCE_BYTES


def mono_to_stereo(input_data: np.ndarray[Any, np.dtype[np.int16]]) -> bytes:
    """Turn mono audio to stereo audio.

    It does it by interleaving data in a new array.
    e.g. [L, R, L, R, L, R, ...]

    Returns:
        Bytes of interleaved data.

    """
    if input_data.ndim != 1:
        raise_msg = (f"Input array must be 1-dimensional, "
                     f"but got shape {input_data.shape}")
        raise ValueError(raise_msg)
    if input_data.size == 0:
        return SILENCE_BYTES

    output_data_np = np.empty((len(input_data) * 2,), dtype=np.int16)
    output_data_np[0::2] = input_data
    output_data_np[1::2] = input_data
    return output_data_np.tobytes()


def resample_to_discord(
    data: bytes,
    source_rate: int,
    target_rate: int,
    resampler: Resampler,
) -> bytes:
    """Resample mono 16-bit PCM audio to stereo 16-bit PCM audio for Discord.

    Uses python-samplerate for higher quality resampling, reducing clicks.

    Returns:
        Bytes of resampled 16-bit stereo PCM audio

    """
    if not data:
        logger.warning("resample_to_discord received empty data.")
        return SILENCE_BYTES
    if source_rate == target_rate:
        try:
            data_np_mono = np.frombuffer(data, dtype=np.int16)
            return mono_to_stereo(data_np_mono)

        except ValueError:
            logger.exception(f"Error converting mono to stereo (rates match). "
                             f"Data length: {len(data)}")
            return SILENCE_BYTES

    try:
        # Input is mono 16-bit PCM (e.g., from Gemini)
        data_np_mono_int16 = np.frombuffer(data, dtype=np.int16)

        # Convert to float for samplerate
        data_np_mono_float = data_np_mono_int16.astype(np.float32) / INT16_MAX

        # Calculate resampling ratio
        ratio = target_rate / source_rate
        local_resampler = resampler
        resampled_data_mono_float = local_resampler.process(
            data_np_mono_float,
            ratio,
            end_of_input=False,
        )

        # Convert back to int16
        resampled_data_mono = resampled_data_mono_float * INT16_MAX
        resampled_data_mono_int16 = resampled_data_mono.astype(np.int16)

        # Convert the resampled mono data to stereo for Discord
        return mono_to_stereo(resampled_data_mono_int16)

    except (samplerate.ResamplingError, ValueError):
        logger.exception(f"Samplerate error during Discord resampling.\n"
                         f"Input data length: {len(data)}\n"
                         f"source_rate: {source_rate}\n"
                         f"target_rate: {target_rate}")
        return SILENCE_BYTES

    except Exception:
        logger.exception("Unexpected error in resample_to_discord.")
        return SILENCE_BYTES


async def process_audio(
        queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        chunk_size: int = 960,
) -> None:
    """Process audio and moves them around between queues.

    Basically, the manager of this entire thing.

    Args:
        queue: Queue for incoming audio bytes.
        output_queue: Queue for processed audio bytes.
        chunk_size: The chunk size. Defaults to 960.

    """
    resampler = samplerate.Resampler(converter_type=ConverterType.sinc_medium)
    while True:
        try:
            audio_bytes = await queue.get()

            if audio_bytes is None:
                await output_queue.put(SILENCE_BYTES)
                continue

            # It's always a multiple of 960
            if len(audio_bytes) % chunk_size != 0:
                logger.error(f"Audio chunk size is not a multiple of {chunk_size}: "
                             f"{len(audio_bytes)}")
                continue

            # Process and queue all chunks
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i : i + chunk_size]
                chunk_resampled = resample_to_discord(chunk, 24000, 48000, resampler)
                await output_queue.put(chunk_resampled)

        except asyncio.CancelledError:
            logger.warning("Audio processing task cancelled")
            break

        except Exception:
            logger.exception("Error in process_audio function.")


async def get_audio(audio_queue: asyncio.Queue) -> AsyncGenerator[bytes, None]:
    """Asynchronously retrieves audio data from a queue and resamples it.

    Args:
        audio_queue: The asyncio.Queue from which to retrieve audio data (bytes).

    Yields:
        bytes: Resampled audio data.

    """
    while True:
        if audio_queue.empty():
            await asyncio.sleep(0.001)
            continue

        data = await audio_queue.get()
        try:
            resampled_data = resample_to_gemini(data, 48000, 16000)
            yield resampled_data

        except Exception:
            logger.exception("An unexpected error in resample function.")

        finally:
            audio_queue.task_done()


async def live(
        audio_queue: asyncio.Queue,
        client: genai.Client,
        model_id: str,
        config: LiveConnectConfig,
) -> asyncio.Task:
    """Connect to the Gemini Live API.

    It streams audio from a queue, and sends it to the API.
    This function establishes a connection with the Gemini Live API,
    retrieves audio data from the provided queue,
    and streams it to the API for processing.
    It also processes data coming back from the API, adding it to the unsorted_queue.
    It handles connection setup, audio streaming, and error logging.

    Args:
        audio_queue: The asyncio.Queue from which to retrieve raw audio data (bytes).
        client:  The Gemini API client object, already initialized and authenticated.
        model_id: The ID of the Gemini model to use for live transcription.
        config: A dictionary containing configuration settings for the Gemini Live API.

    """
    process_task = asyncio.create_task(process_audio(unsorted_queue, sorted_queue))

    try:
        async def audio_stream() -> AsyncGenerator[bytes, None]:
            stream = get_audio(audio_queue)
            async for stream_data in stream:
                yield stream_data

        async with client.aio.live.connect(model=model_id, config=config) as session:
            logger.info("Connected to Gemini Live API.")
            async for data in session.start_stream(
                    stream=audio_stream(),
                    mime_type="audio/pcm",
            ):
                await unsorted_queue.put(data.data)

    except Exception:
        logger.exception("An unexpected error happened in live function.")

    return process_task
