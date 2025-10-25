import asyncio
import logging
from asyncio import create_task as original_asyncio_create_task
from collections.abc import AsyncGenerator, Coroutine
from typing import Any, TypeVar
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
import samplerate
from _pytest.logging import LogCaptureFixture
from discord.ext import voice_recv
from google.genai.types import Blob, LiveConnectConfig

from packages import audio

_T = TypeVar("_T")

class MockLiveSession:
    """Mock object representing the Gemini Live Session context manager."""
    async def __aenter__(self) -> "MockLiveSession":
        """Enter the context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Exit the context manager."""

# --- Fixtures and existing tests remain unchanged ---
@pytest.fixture
def discord_pcm_audio_chunk() -> bytes:
    """A chunk of PCM audio data from Discord, 48kHz, 32-bit, stereo."""
    num_samples = 960 * 2
    data_np = (np.sin(
        np.linspace(0, 440 * 2 * np.pi, num_samples),
    ) * (2**31 - 1)).astype(np.int32)
    return data_np.tobytes()

@pytest.fixture
def gemini_pcm_audio_chunk() -> bytes:
    """A chunk of PCM audio data for Gemini, 16kHz, 16-bit, mono."""
    num_samples = 480
    data_np = (np.sin(
        np.linspace(0, 440 * 2 * np.pi, num_samples),
    ) * audio.INT16_MAX).astype(np.int16)
    return data_np.tobytes()

def test_resample_to_gemini(discord_pcm_audio_chunk: bytes) -> None:
    """Tests that the resample_to_gemini function correctly resamples audio data."""
    expected_length = 1280

    resampled_data = audio.resample_to_gemini(discord_pcm_audio_chunk, 48000, 16000)
    assert len(resampled_data) == expected_length

def test_resample_to_gemini_empty_input() -> None:
    """Test that the resample_to_gemini function correctly handles empty data."""
    assert audio.resample_to_gemini(b"", 48000, 16000) == audio.SILENCE_BYTES

def test_resample_to_gemini_same_rate(discord_pcm_audio_chunk: bytes) -> None:
    """Test that resample_to_gemini function correctly handles if the sr is equal."""
    expected_length = 3840
    resampled_data = audio.resample_to_gemini(discord_pcm_audio_chunk, 48000, 48000)

    assert len(resampled_data) == expected_length
    data_np = np.frombuffer(resampled_data, dtype=np.int16)
    assert data_np.dtype == np.int16

@patch(
    "packages.audio.samplerate.resample",
    side_effect=samplerate.ResamplingError("Mock Error"),
)
def test_resample_to_gemini_samplerate_error(
    mock_resample: Mock,
    discord_pcm_audio_chunk: bytes,
    caplog: LogCaptureFixture,
) -> None:
    """Test that the resample_to_gemini function correctly handles samplerate errors."""
    print(discord_pcm_audio_chunk)
    caplog.at_level(logging.ERROR)
    result = audio.resample_to_gemini(discord_pcm_audio_chunk, 48000, 16000)
    assert result == audio.SILENCE_BYTES
    assert "Samplerate error" in caplog.text

@patch("packages.audio.np.frombuffer", side_effect=ValueError("Mock Error"))
def test_resample_to_gemini_general_exception(discord_pcm_audio_chunk: bytes) -> None:
    """Test that the resample_to_gemini function correctly handles exceptions."""
    result = audio.resample_to_gemini(discord_pcm_audio_chunk, 48000, 16000)
    assert result == audio.SILENCE_BYTES

def test_mono_to_stereo(gemini_pcm_audio_chunk: bytes) -> None:
    """Tests that the mono_to_stereo function correctly converts mono data to stereo."""
    mono_data = np.frombuffer(gemini_pcm_audio_chunk, dtype=np.int16)
    stereo_bytes = audio.mono_to_stereo(mono_data)
    assert len(stereo_bytes) == len(gemini_pcm_audio_chunk) * 2

def test_mono_to_stereo_empty() -> None:
    """Test that the mono_to_stereo function correctly handles empty input."""
    empty_data = np.array([], dtype=np.int16)
    assert audio.mono_to_stereo(empty_data) == audio.SILENCE_BYTES

def test_mono_to_stereo_wrong_ndim() -> None:
    """Test that the mono_to_stereo function correctly handles input > 1 dimension."""
    two_d_data = np.array([[1, 2], [3, 4]], dtype=np.int16)
    with pytest.raises(ValueError, match="Input array must be 1-dimensional"):
        audio.mono_to_stereo(two_d_data)


def test_resample_to_discord(gemini_pcm_audio_chunk: bytes) -> None:
    """Tests that the resample_to_discord function correctly resamples audio data."""
    expected_bytes = 3464

    resampler = samplerate.Resampler(
        converter_type=samplerate.ConverterType.sinc_medium,
    )
    resampled_data = audio.resample_to_discord(
        gemini_pcm_audio_chunk, 24000, 48000, resampler,
    )
    assert len(resampled_data) == expected_bytes

def test_resample_to_discord_empty_data() -> None:
    """Test if the resample_to_discord function correctly handles empty data."""
    resampler = samplerate.Resampler(
        converter_type=samplerate.ConverterType.sinc_medium,
    )
    assert audio.resample_to_discord(
        b"", 24000, 48000, resampler,
    ) == audio.SILENCE_BYTES

def test_resample_to_discord_same_rate(gemini_pcm_audio_chunk: bytes) -> None:
    """Test if the resample_to_discord function correctly handles if the sr is equal."""
    resampler = samplerate.Resampler(
        converter_type=samplerate.ConverterType.sinc_medium,
    )
    stereo_bytes = audio.resample_to_discord(
        gemini_pcm_audio_chunk,
        24000, 24000,
        resampler,
    )
    assert len(stereo_bytes) == len(gemini_pcm_audio_chunk) * 2

@patch("packages.audio.mono_to_stereo", side_effect=ValueError("Mono Error"))
def test_resample_to_discord_same_rate_mono_error(
    mock_mono_to_stereo: Mock,
    gemini_pcm_audio_chunk: bytes,
) -> None:
    """Test that the resample_to_discord function correctly handles mono errors."""
    resampler = samplerate.Resampler(
        converter_type=samplerate.ConverterType.sinc_medium,
    )
    result = audio.resample_to_discord(gemini_pcm_audio_chunk, 24000, 24000, resampler)
    assert result == audio.SILENCE_BYTES

@patch(
    "packages.audio.samplerate.Resampler.process",
    side_effect=samplerate.ResamplingError("Mock Error"),
)
def test_resample_to_discord_samplerate_error(gemini_pcm_audio_chunk: bytes) -> None:
    """Test that the resample_to_discord function handles samplerate errors."""
    resampler = samplerate.Resampler(
        converter_type=samplerate.ConverterType.sinc_medium,
    )
    result = audio.resample_to_discord(gemini_pcm_audio_chunk, 24000, 48000, resampler)
    assert result == audio.SILENCE_BYTES

@patch("packages.audio.np.frombuffer", side_effect=ValueError("General Error"))
def test_resample_to_discord_general_exception(gemini_pcm_audio_chunk: bytes) -> None:
    """Test that the resample_to_discord function handles exceptions."""
    resampler = samplerate.Resampler(
        converter_type=samplerate.ConverterType.sinc_medium,
    )
    result = audio.resample_to_discord(gemini_pcm_audio_chunk, 24000, 48000, resampler)
    assert result == audio.SILENCE_BYTES

def test_audio_sink() -> None:
    """Tests the AudioSink class."""
    mock_voice_data = MagicMock(spec=voice_recv.VoiceData, pcm=b"\x01\x02\x03\x04")
    q = asyncio.Queue()
    sink = audio.AudioSink(q)
    sink.write(None, mock_voice_data)
    assert q.get_nowait() == b"\x01\x02\x03\x04"

def test_audio_sink_wants_opus() -> None:
    """Tests the AudioSink.wants_opus method."""
    sink = audio.AudioSink(asyncio.Queue())
    assert sink.wants_opus() is False

def test_audio_sink_cleanup() -> None:
    """Tests the AudioSink.cleanup method."""
    sink = audio.AudioSink(asyncio.Queue())
    # Should run without error
    sink.cleanup()

@pytest.mark.asyncio
async def test_audio_source() -> None:
    """Tests the AudioSource class."""
    q = asyncio.Queue()
    source = audio.AudioSource()
    source.stream = q
    assert source.read() == audio.SILENCE_BYTES
    await q.put(b"\xde\xad\xbe\xef")
    assert source.read() == b"\xde\xad\xbe\xef"

def test_audio_source_is_opus() -> None:
    """Tests the AudioSource.is_opus method."""
    source = audio.AudioSource()
    assert source.is_opus() is False

@pytest.mark.asyncio
@patch(
    "packages.audio.asyncio.Queue.get_nowait",
    side_effect=Exception("Test Error"),
)
async def test_audio_source_read_exception(mock_get_nowait: Mock) -> None:
    """Test if the AudioSource.read method correctly handles exceptions."""
    source = audio.AudioSource()
    assert source.read() == audio.SILENCE_BYTES

@pytest.mark.asyncio
async def test_process_audio(gemini_pcm_audio_chunk: bytes) -> None:
    """Tests the process_audio function."""
    input_q, output_q = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(
        audio.process_audio(
            input_q,
            output_q,
            chunk_size=len(gemini_pcm_audio_chunk),
        ),
    )
    try:
        await input_q.put(gemini_pcm_audio_chunk)
        await asyncio.wait_for(output_q.get(), timeout=1.0)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
async def test_process_audio_none_input() -> None:
    """Test if the process_audio function correctly handles None input."""
    input_q, output_q = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(audio.process_audio(input_q, output_q, chunk_size=10))
    try:
        await input_q.put(None)
        result = await asyncio.wait_for(output_q.get(), timeout=0.1)
        assert result == audio.SILENCE_BYTES
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
async def test_process_audio_misaligned_chunk() -> None:
    """Test if the process_audio function correctly handles misaligned chunks."""
    input_q, output_q = asyncio.Queue(), asyncio.Queue()
    misaligned_data = b"\x00" * 961
    task = asyncio.create_task(audio.process_audio(input_q, output_q))
    try:
        await input_q.put(misaligned_data)
        await asyncio.sleep(0.01)

        assert output_q.empty()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
@patch("packages.audio.resample_to_discord", side_effect=ValueError("Process Error"))
async def test_process_audio_general_exception(mock_resample: Mock) -> None:
    """Test if the process_audio function correctly handles general exceptions."""
    input_q, output_q = asyncio.Queue(), asyncio.Queue()
    valid_data = b"\x00" * 960
    task = asyncio.create_task(audio.process_audio(input_q, output_q))
    try:
        await input_q.put(valid_data)
        await asyncio.sleep(0.01)

        assert not task.done()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
async def test_send_audio_to_gemini(discord_pcm_audio_chunk: bytes) -> None:
    """Tests the _send_audio_to_gemini function."""
    mock_session = MagicMock(send_realtime_input=AsyncMock())
    q = asyncio.Queue()
    task = asyncio.create_task(audio._send_audio_to_gemini(mock_session, q))
    try:
        await q.put(discord_pcm_audio_chunk)
        await q.join()

        data = audio.resample_to_gemini(
            discord_pcm_audio_chunk,
            48000,
            16000,
        )

        mock_session.send_realtime_input.assert_awaited_once_with(
            audio=Blob(data=data, mime_type="audio/pcm;rate=16000"),
        )
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
@patch("packages.audio.resample_to_gemini", side_effect=Exception("Gemini Send Error"))
async def test_send_audio_to_gemini_exception(
    mock_resample: Mock,
    discord_pcm_audio_chunk: bytes,
) -> None:
    """Test if the _send_audio_to_gemini function correctly handles exceptions."""
    mock_session = MagicMock(send=AsyncMock())
    q = asyncio.Queue()
    task = asyncio.create_task(audio._send_audio_to_gemini(mock_session, q))
    try:
        await q.put(discord_pcm_audio_chunk)
        await asyncio.sleep(0.01)
        # The exception is caught, task_done() should still be called
        assert q.empty()
        mock_session.send.assert_not_awaited()
        # Task should continue running
        assert not task.done()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
async def test_receive_audio_from_gemini() -> None:
    """Tests the _receive_audio_from_gemini function."""
    async def mock_turn_generator() -> AsyncGenerator[MagicMock, None]:
        yield MagicMock(data=b"\xca\xfe")

    mock_session = MagicMock(receive=MagicMock(return_value=mock_turn_generator()))
    q = asyncio.Queue()
    task = asyncio.create_task(audio._receive_audio_from_gemini(mock_session, q))

    try:
        result = await asyncio.wait_for(q.get(), timeout=1.0)
        assert result == b"\xca\xfe"
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
async def test_receive_audio_from_gemini_exception() -> None:
    """Test if the _receive_audio_from_gemini function correctly handles exceptions."""
    async def failing_turn_generator() -> None:
        msg = "API Receive Error"

        await asyncio.sleep(0)
        raise Exception(msg)

    mock_session = MagicMock(receive=MagicMock(return_value=failing_turn_generator()))
    q = asyncio.Queue()
    task = asyncio.create_task(audio._receive_audio_from_gemini(mock_session, q))

    try:
        # Give time for the error loop to run (it sleeps for 1s on error)
        await asyncio.sleep(0.1)

        # Task should continue running
        assert not task.done()
        assert q.empty()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

@pytest.mark.asyncio
@patch("packages.audio.process_audio")
@patch("packages.audio._send_audio_to_gemini", new_callable=AsyncMock)
@patch("packages.audio._receive_audio_from_gemini", new_callable=AsyncMock)
@patch("packages.audio.asyncio.create_task")
async def test_live_connection_lifecycle(
    mock_create_task: Mock,
    mock_receive_audio: AsyncMock,
    mock_send_audio: AsyncMock,
    mock_process_audio_func: AsyncMock,
) -> None:
    """Tests the connection establishment, task creation, and cleanup flow of live()."""
    process_task_instance = None

    def mock_create_task_side_effect(
        coro: Coroutine[Any, Any, _T],
        **kwargs,
    ) -> asyncio.Task:
        nonlocal process_task_instance
        real_task = original_asyncio_create_task(coro, **kwargs)
        if process_task_instance is None:
            process_task_instance = real_task
        return real_task

    mock_create_task.side_effect = mock_create_task_side_effect

    async def blocking_process_coro(
        queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        chunk_size: int = 960,
    ) -> None:
        await asyncio.Future()

    mock_process_audio_func.side_effect = blocking_process_coro

    audio.unsorted_queue = asyncio.Queue(maxsize=2)
    audio.sorted_queue = asyncio.Queue(maxsize=2)

    mock_client = MagicMock()
    audio_queue = asyncio.Queue()

    mock_connect = MagicMock(return_value=MockLiveSession())
    mock_client.aio.live.connect = mock_connect

    mock_send_audio.side_effect = blocking_process_coro
    mock_receive_audio.side_effect = blocking_process_coro

    live_task = original_asyncio_create_task(
        audio.live(
            audio_queue=audio_queue,
            client=mock_client,
            model_id="test_model",
            config=LiveConnectConfig(),
        ),
    )

    await asyncio.sleep(0.01)

    assert process_task_instance is not None
    mock_connect.assert_called_once_with(model="test_model", config=LiveConnectConfig())
    mock_process_audio_func.assert_called_once_with(
        audio.unsorted_queue,
        audio.sorted_queue,
    )
    mock_send_audio.assert_called_once()
    mock_receive_audio.assert_called_once()
    assert not live_task.done()

    live_task.cancel()

    returned_process_task = None

    try:
        returned_process_task = await live_task
    except asyncio.CancelledError:
        pytest.fail(
            "live() task failed to handle CancelledError "
            "internally during cancellation path.",
        )

    assert returned_process_task is process_task_instance
    assert returned_process_task.done()
    assert returned_process_task.cancelled()


@pytest.mark.asyncio
@patch("packages.audio.process_audio")
@patch("packages.audio.asyncio.create_task")
async def test_live_connection_failure(
    mock_create_task: Mock,
    mock_process_audio_func: AsyncMock,
) -> None:
    """Tests the error handling and cleanup when the Gemini connection fails."""
    process_task_instance = None

    def mock_create_task_side_effect(
        coro: Coroutine[Any, Any, _T],
        **kwargs,
    ) -> asyncio.Task:
        nonlocal process_task_instance
        real_task = original_asyncio_create_task(coro, **kwargs)
        if process_task_instance is None:
            process_task_instance = real_task
        return real_task

    mock_create_task.side_effect = mock_create_task_side_effect

    async def blocking_process_coro() -> None:
        await asyncio.Future()

    mock_process_audio_func.side_effect = blocking_process_coro

    mock_client = MagicMock()
    connection_error = ValueError("Connection Failed")
    mock_connect = MagicMock(side_effect=connection_error)
    mock_client.aio.live.connect = mock_connect

    audio.unsorted_queue = asyncio.Queue()
    audio.sorted_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()

    # The `live` function is expected to re-raise the connection error.
    with pytest.raises(ValueError, match="Connection Failed"):
        await audio.live(
            audio_queue=audio_queue,
            client=mock_client,
            model_id="test_model",
            config=LiveConnectConfig(),
        )

    mock_connect.assert_called_once_with(model="test_model", config=LiveConnectConfig())

    mock_process_audio_func.assert_called_once_with(
        audio.unsorted_queue,
        audio.sorted_queue,
    )
    assert process_task_instance is not None, "process_task was not created"

    await asyncio.sleep(0)

    assert process_task_instance.done()
    assert process_task_instance.cancelled()
