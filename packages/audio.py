import asyncio
import numpy as np
from discord.ext import voice_recv
import discord
import samplerate
import logging
import traceback
from typing import Any

from samplerate import ConverterType

unsorted_queue = asyncio.Queue(maxsize=15)
sorted_queue = asyncio.Queue(maxsize=15)

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

class AudioSource(discord.PCMAudio):
    def __init__(self):
        self.stream = sorted_queue

    def read(self):
        try:
            chunk = self.stream.get_nowait()
            return chunk
        except asyncio.QueueEmpty:
            return bytes(3840)
        except Exception:
            logging.error(traceback.format_exc())
            return bytes(3840)

    def is_opus(self):
        return False

def resample_to_gemini(data: bytes, source_rate: int, target_rate: int) -> bytes:
    """Resamples 48kHz 32-bit Discord PCM audio to 16kHz 16-bit Gemini PCM audio."""
    if not data:
        return b''
    if source_rate == target_rate:
        # Even if rates match, we need to convert bit depth
        data_np = np.frombuffer(data, dtype=np.int32)
        # Scale 32-bit [-2^31, 2^31-1] down to 16-bit [-2^15, 2^15-1]
        # Right shift by 16 bits effectively divides by 2^16
        rescaled_data = (data_np // (2**16)).astype(np.int16)
        return rescaled_data.tobytes()

    try:
        data_np_int32 = np.frombuffer(data, dtype=np.int32)
        data_np_float64 = data_np_int32.astype(np.float64) / (2**31)

        ratio = target_rate / source_rate
        resampled_data_float = samplerate.resample(data_np_float64, ratio, 'sinc_medium')
        resampled_data_int16 = (resampled_data_float * 32767).astype(np.int16)

        return resampled_data_int16.tobytes()

    except samplerate.ResamplingError as e:
        logging.error(f"Samplerate error during Gemini resampling: {e} - Input data length: {len(data)}")
        return b''
    except Exception:
        logging.error(f"Unexpected error in resample_to_gemini: {traceback.format_exc()}")
        return b''

def mono_to_stereo(input_data: np.ndarray[Any, np.dtype[np.int16]]):
    if input_data.ndim != 1:
        raise ValueError(
            f"Input array must be 1-dimensional, but got shape {input_data.shape}"
        )
    if input_data.size == 0:
        return b''

    output_data_np = np.empty((len(input_data) * 2,), dtype=np.int16)
    output_data_np[0::2] = input_data
    output_data_np[1::2] = input_data
    return output_data_np.tobytes()

def resample_to_discord(data: bytes, source_rate: int, target_rate: int, resampler) -> bytes:
    """
    Resamples mono 16-bit PCM audio (from Gemini, likely 24kHz)
    to stereo 16-bit PCM audio for Discord (48kHz).
    Uses python-samplerate for higher quality resampling, reducing clicks.
    """
    if not data:
        logging.warning("resample_to_discord received empty data.")
        return b''
    if source_rate == target_rate:
        # If rates match, just convert mono to stereo
        try:
            data_np_mono = np.frombuffer(data, dtype=np.int16)
            return mono_to_stereo(data_np_mono)
        except ValueError as e:
             logging.error(f"Error converting mono to stereo (rates match): {e}. Data length: {len(data)}")
             return b'' # Return empty bytes on error


    try:
        # Input is mono 16-bit PCM (e.g., from Gemini)
        data_np_mono_int16 = np.frombuffer(data, dtype=np.int16)

        # Convert to float for samplerate
        data_np_mono_float = data_np_mono_int16.astype(np.float32) / 32767.0

        # Calculate resampling ratio
        ratio = target_rate / source_rate
        local_resampler = resampler
        resampled_data_mono_float = local_resampler.process(
            data_np_mono_float, ratio, end_of_input=False
        )

        # Convert back to int16
        resampled_data_mono_int16 = (resampled_data_mono_float * 32767.0).astype(np.int16)

        # Convert the resampled mono data to stereo for Discord
        stereo_data_bytes = mono_to_stereo(resampled_data_mono_int16)

        return stereo_data_bytes

    except samplerate.ResamplingError as e:
        logging.error(f"Samplerate error during Discord resampling: {e} - Input data length: {len(data)}, source_rate: {source_rate}, target_rate: {target_rate}")
        return b''
    except ValueError as e:
        logging.error(f"ValueError during Discord resampling: {e}. Data length: {len(data)}, Source Rate: {source_rate}, Target Rate: {target_rate}")
        return b''
    except Exception:
        logging.error(f"Unexpected error in resample_to_discord: {traceback.format_exc()}")
        return b''

async def process_audio(
    queue: asyncio.Queue, output_queue: asyncio.Queue, chunk_size: int = 960
):

    resampler = samplerate.Resampler(converter_type=ConverterType.sinc_medium)
    while True:
        try:
            audio_bytes = await queue.get()

            if audio_bytes is None:
                await output_queue.put(None) # Propagate signal if needed
                queue.task_done()
                break

            # It's always a multiple of 960
            if len(audio_bytes) % chunk_size != 0:
                logging.error(f"Audio chunk size is not a multiple of {chunk_size}: {len(audio_bytes)}")
                continue

            # Process and queue all chunks
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i : i + chunk_size]
                chunk_resampled = resample_to_discord(chunk, 24000, 48000, resampler)
                await output_queue.put(chunk_resampled)

        except asyncio.CancelledError:
            logging.warning("Audio processing task cancelled")
            break
        except Exception:
            logging.error(f"Error in process_audio function: {traceback.format_exc()}")

async def get_audio(audio_queue: asyncio.Queue):
    while True:
        if audio_queue.empty():
            await asyncio.sleep(0.001)
            continue

        data = await audio_queue.get()
        try:
            resampled_data = resample_to_gemini(data, 48000, 16000)
            yield resampled_data
        except Exception as e:
            logging.error(f"Error in resample function: {e}")
        finally:
            audio_queue.task_done()

async def live(audio_queue, client, model_id, config):
    asyncio.create_task(process_audio(unsorted_queue, sorted_queue))

    try:
        async def audio_stream():
            stream = get_audio(audio_queue)
            async for stream_data in stream:
                yield stream_data

        async with client.aio.live.connect(model=model_id, config=config) as session:
            logging.info("Connected to Gemini Live API.")
            async for data in session.start_stream(stream=audio_stream(), mime_type='audio/pcm'):
                await unsorted_queue.put(data.data)
    except Exception as e:
        logging.error(f"Error in live function: {e}")
