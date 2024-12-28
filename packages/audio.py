import asyncio
import numpy as np
from librosa import resample

def resample_audio(data: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return data

    # Convert byte data to a NumPy array of floats (normalized to approximately [-1, 1])
    data_np = np.frombuffer(data, dtype=np.int32).astype(np.float32) / (2 ** 31 - 1)

    # Resample the audio data using librosa
    resampled_data = resample(data_np, orig_sr=source_rate, target_sr=target_rate)

    # Check for NaN values
    if np.isnan(resampled_data).any():
        print("Warning: NaN values detected in resampled audio.")
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
            print(f"Error in resample function: {e}")
        finally:
            audio_queue.task_done()


async def live(audio_queue, client, model_id, config):
    async def audio_stream():
        stream = get_audio(audio_queue)
        async for stream_data in stream:
            yield stream_data

    async with client.aio.live.connect(model=model_id, config=config) as session:
        print("Connected. Please wait for 10 seconds as it will not work instantly for whatever reason.")
        async for data in session.start_stream(stream=audio_stream(), mime_type='audio/pcm'):
            print(data.text if not None else "\n", end='')