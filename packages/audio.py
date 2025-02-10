import asyncio
import numpy as np
from discord.ext import voice_recv
import discord
from librosa import resample
import logging
import traceback

unsorted_queue = asyncio.Queue(maxsize=200)
sorted_queue = asyncio.Queue(maxsize=200)

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
            # Returns empty bytes
            return bytes(3840)
        except Exception:
            # log error with the traceback
            logging.error(traceback.format_exc())

            # Returns empty bytes
            return bytes(3840)

    def is_opus(self):
        return False

def resample_audio(data: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return data

    # Convert byte data to a NumPy array of floats (normalized to approximately [-1, 1])
    data_np = np.frombuffer(data, dtype=np.int32).astype(np.float64) / (2 ** 31 - 1)

    # Resample the audio data using librosa
    resampled_data = resample(data_np, orig_sr=source_rate, target_sr=target_rate)

    # Check for NaN values
    if np.isnan(resampled_data).any():
        logging.warning("NaN values detected in resampled audio.")
        resampled_data = np.nan_to_num(resampled_data, nan=0)

    # Scale back to int16 range and convert to int16
    resampled_data_int = (resampled_data * (2 ** 15 - 1)).astype(np.int16)

    return resampled_data_int.tobytes()

# TODO refactor this with the above function, and fix the clicking sound
def resample_audio_2(data: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return data

    # Convert byte data to a NumPy array of floats (normalized to approximately [-1, 1])
    data_np = np.frombuffer(data, dtype=np.int16).astype(np.float64) / (2 ** 15 - 1)

    # Resample the audio data using librosa
    resampled_data = resample(data_np, orig_sr=source_rate, target_sr=target_rate)

    # Check for NaN values
    if np.isnan(resampled_data).any():
        logging.warning("NaN values detected in resampled audio.")
        resampled_data = np.nan_to_num(resampled_data, nan=0)

    # Scale back to int16 range and convert to int16
    resampled_data_int = (resampled_data * (2 ** 15 - 1)).astype(np.int16)

    # TODO seperate this into a seperate function
    interleaved_data = np.empty((1920,), dtype=np.int16)
    interleaved_data[0::2] = resampled_data_int
    interleaved_data[1::2] = resampled_data_int

    return interleaved_data.tobytes()

async def get_audio(audio_queue: asyncio.Queue):
    while True:
        if audio_queue.empty():
            await asyncio.sleep(0.001)  # Short pause to avoid excessive CPU usage
            continue

        data = await audio_queue.get()
        try:
            resampled_data = resample_audio(data, 48000, 16000)
            yield resampled_data
        except Exception as e:
            logging.error(f"Error in resample function: {e}")
        finally:
            audio_queue.task_done()

async def process_audio(queue: asyncio.Queue, output_queue: asyncio.Queue, chunk_size: int = 960):  # Kind of sketchy since the docstring says that it is supposed to be 3840 but whatever
    buffer = bytearray()
    start = 0  # Track the start of unprocessed data

    while True:
        try:
            audio_bytes = await queue.get()
            # Extend buffer with new data; None is treated as empty bytes
            buffer.extend(audio_bytes if audio_bytes is not None else b'')

            # Process as many chunks as possible from the current buffer
            while len(buffer) - start >= chunk_size:
                end = start + chunk_size
                chunk = bytes(buffer[start:end])
                chunk_resampled = resample_audio_2(chunk, 24000, 48000)
                await output_queue.put(chunk_resampled)
                start = end  # Move the start forward by the chunk size

            # Trim processed data from the buffer and reset start if needed
            if start > 0:
                buffer = buffer[start:]
                start = 0

        except asyncio.CancelledError:
            logging.warning("Audio processing task cancelled")
            break
        except Exception:
            logging.error(f"Error in process_audio function: {traceback.format_exc()}")

async def live(audio_queue, client, model_id, config):
    asyncio.create_task(process_audio(unsorted_queue, sorted_queue))

    try:
        async def audio_stream():
            stream = get_audio(audio_queue)
            async for stream_data in stream:
                yield stream_data

        async with client.aio.live.connect(model=model_id, config=config) as session:
            print("Connected. Please wait for 10 seconds as it will not work instantly for whatever reason.")
            async for data in session.start_stream(stream=audio_stream(), mime_type='audio/pcm'):
                await unsorted_queue.put(data.data)
    except Exception as e:
        logging.error(f"Error in live function: {e}")
