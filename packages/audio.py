import asyncio
import numpy as np
from discord.ext import voice_recv
import discord
from librosa import resample
import logging

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
        except Exception as e:
            logging.error(f"Error in AudioSource.read function: {e}")

            # Returns empty bytes
            return bytes(3840)

    def is_opus(self):
        return False

def resample_audio(data: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return data

    # Convert byte data to a NumPy array of floats (normalized to approximately [-1, 1])
    data_np = np.frombuffer(data, dtype=np.int32).astype(np.float32) / (2 ** 31 - 1)

    # Resample the audio data using librosa
    resampled_data = resample(data_np, orig_sr=source_rate, target_sr=target_rate)

    # Check for NaN values
    if np.isnan(resampled_data).any():
        logging.warning("NaN values detected in resampled audio.")
        resampled_data = np.nan_to_num(resampled_data, nan=0)

    # Scale back to int16 range and convert to int16
    resampled_data_int = (resampled_data * (2 ** 15 - 1)).astype(np.int16)

    return resampled_data_int.tobytes()


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

async def process_audio(queue: asyncio.Queue, output_queue: asyncio.Queue, chunk_size: int = 3840):
    # Initialize an empty bytearray to store incoming audio data.
    buffer = bytearray()

    while True:
        try:
            # Get audio bytes from the input queue.
            audio_bytes = await queue.get()

            # If audio_bytes is not None, extend the buffer with the new audio data. If None, extend by empty bytes to skip adding it to the buffer
            buffer.extend(audio_bytes if audio_bytes is not None else b'')

            # Process audio chunks while the buffer has enough data to form a complete chunk.
            while len(buffer) >= chunk_size:
                # Extract a chunk of audio data from the buffer.
                chunk = bytes(buffer[:chunk_size])

                del buffer[:chunk_size]
                await output_queue.put(chunk)
        except asyncio.CancelledError:
            logging.warning("Audio processing task cancelled")
            break
        except Exception as e:
            logging.error(f"Error in process_audio function: {e}")



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
