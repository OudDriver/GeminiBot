import io
from unittest.mock import AsyncMock, Mock, call, patch

import discord
import pytest

import packages.utilities.general_utils as utils

SPLIT_MESSAGES_CASES = [
    # Case 1: Basic splitting, prioritizing spaces (L=15)
    (
        "This is a test message that needs to be split properly.",
        15,
        [
            "This is a test",
            "message that",
            "needs to be",
            "split properly.",
        ],
    ),

    # Case 2: Forcing a word break because no space is available within limit (L=8)
    (
        "Averylongword next",
        8,
        [
            "Averylon",
            "gword",
            "next",
        ],
    ),

    # Case 3: Space exists but is too far back (L=5)
    (
        "WordSplit Test Message",
        5,
        [
            "WordS",
            "plit",
            "Test",
            "Messa",
            "ge",
        ],
    ),

    # Case 4: Length boundary exactly hits a space (L=6)
    (
        "Hello World",
        6,
        [
            "Hello",
            "World",
        ],
    ),

    # Case 5: Handling leading/multiple spaces (Should discard spaces between chunks)
    (
        "ChunkA   ChunkB",
        8,
        [
            "ChunkA",
            "ChunkB",
        ],
    ),

    # Case 6: Very short limit (L=1)
    ("A B C", 1, ["A", "B", "C"]),

    # Case 7: Very long word requiring multiple forced breaks
    (
        "Pneumonoultramicroscopicsilicovolcanoconiosis",
        10,
        [
            "Pneumonoul",
            "tramicrosc",
            "opicsilico",
            "volcanocon",
            "iosis",
        ],
    ),
]

ENSURE_LIST_CASES = [
    ("A string", ["A string"]),
    (["A", "list"], ["A", "list"]),
    (("A", "tuple"), [("A", "tuple")]), # A tuple should not be converted to a list.
    (42, [42]),
    (None, []),
    (True, [True]),
    ([["2", "D"], ["A", "Raise"]], [["2", "D"], ["A", "Raise"]]),
    ((["2", "D"], ["A", "Tuple?"]), [(["2", "D"], ["A", "Tuple?"])]),
]

@patch("packages.utilities.general_utils.uuid.uuid4")
@patch("packages.utilities.general_utils.time.time")
def test_generate_unique_file_name(mock_time: Mock, mock_uuid: Mock) -> None:
    """Test if generate_unique_file_name is working.

    The format should be the timestamp, the uuid4, and the extension.
    """
    mock_time.return_value = 314159265
    mock_uuid.return_value = "uuid4"

    result = utils.generate_unique_file_name("png")

    assert result == "314159265_uuid4.png"

    mock_time.assert_called_once_with()
    mock_uuid.assert_called_once_with()

def test_generate_unique_file_name_no_extension() -> None:
    """Test if generate_unique_file_name raises an error if no extension is provided."""
    with pytest.raises(ValueError) as exc_info:
        utils.generate_unique_file_name("")

    assert str(exc_info.value) == "No extension provided!"

@patch("packages.utilities.general_utils.uuid.uuid4")
@patch("packages.utilities.general_utils.time.time")
def test_generate_unique_file_name_dot_extension(
    mock_time: Mock, mock_uuid: Mock,
) -> None:
    """Test if the function correct handles extensions starting with a dot."""
    mock_time.return_value = 314159265
    mock_uuid.return_value = "uuid4"

    result = utils.generate_unique_file_name(".png")

    assert result == "314159265_uuid4.png"

    mock_time.assert_called_once_with()
    mock_uuid.assert_called_once_with()

def test_convert_subscripts() -> None:
    """Test if convert_subscripts is working."""
    result = utils.convert_subscripts(
        "Glucose is C<sub>6</sub>H<sub>12</sub>O<sub>6</sub>.",
    )

    assert result == "Glucose is C₆H₁₂O₆."

def test_convert_subscripts_empty() -> None:
    """Test if convert_subscripts handles empty strings correctly."""
    result = utils.convert_subscripts("")
    assert result == ""

def test_convert_superscripts() -> None:
    """Test if convert_subscripts is working."""
    result = utils.convert_superscripts(
        "The derivative of x<sup>2</sup> is 2x.",
    )

    assert result == "The derivative of x² is 2x."

def test_convert_superscripts_empty() -> None:
    """Test if convert_superscripts handles empty strings correctly."""
    result = utils.convert_superscripts("")
    assert result == ""

def test_clean_text() -> None:
    """Test if clean_text is working."""
    result = utils.clean_text(
        "<store>Badcrow is an idiot</store>\n"
        "The famous equation is E = mc<sup>2</sup>.\n"
        "<store>So is Mutanzom</store>",
    )

    assert result[0] == "\nThe famous equation is E = mc².\n"
    assert result[1] == ["<store>Badcrow is an idiot</store>", "<store>So is Mutanzom</store>"]

def test_clean_text_empty() -> None:
    """Test if clean_text handles empty strings correctly."""
    result = utils.clean_text("")
    assert result == ("", [])

@patch(
    "packages.utilities.general_utils.convert_subscripts",
    side_effect=lambda x: x,
)
@patch(
    "packages.utilities.general_utils.convert_superscripts",
    side_effect=lambda x: x,
)
@patch("packages.utilities.general_utils.regex.findall")
@patch("packages.utilities.general_utils.regex.sub")
def test_clean_text_calls(
    mock_sub: Mock,
    mock_findall: Mock,
    mock_convert_superscripts: Mock,
    mock_convert_subscripts: Mock,
) -> None:
    """Test if clean_text is calling the correct functions."""
    utils.clean_text("Doesn't matter.")

    mock_convert_superscripts.assert_called_once_with("Doesn't matter.")
    mock_convert_subscripts.assert_called_once_with("Doesn't matter.")
    mock_sub.assert_called_once()
    mock_findall.assert_called_once()

@pytest.mark.parametrize(("message", "length", "expected_chunks"), SPLIT_MESSAGES_CASES)
def test_split_message(
    message: str,
    length: int,
    expected_chunks: list[str],
) -> None:
    """Test various scenarios involving space preference and mandatory breaks."""
    result = list(utils.split_message_chunks(message, length))
    assert result == expected_chunks

def test_split_message_chunk_empty() -> None:
    """Test handling of an empty input message."""
    assert list(utils.split_message_chunks("", 10)) == []

def test_split_message_shorter_than_length() -> None:
    """Test a message that fits entirely in one chunk."""
    message = "This is short."
    length = 50
    assert list(utils.split_message_chunks(message, length)) == ["This is short."]

def test_split_message_exact_length() -> None:
    """Test a message that is exactly the specified length."""
    message = "0123456789"
    length = 10
    assert list(utils.split_message_chunks(message, length)) == ["0123456789"]

def test_split_message_length_negative() -> None:
    """Test handling if length is negative."""
    with pytest.raises(ValueError) as exc_info:
        list(utils.split_message_chunks("", -10))

    assert str(exc_info.value) == "Length limit must be positive."

def test_split_message_length_zero() -> None:
    """Test handling if length is zero."""
    with pytest.raises(ValueError) as exc_info:
        list(utils.split_message_chunks("", 0))

    assert str(exc_info.value) == "Length limit must be positive."

@pytest.mark.asyncio
async def test_send_long_message() -> None:
    """Tests that a long message is correctly split into chunks and sent."""
    mock_ctx = AsyncMock()
    long_message = "This is a very long message that needs to be split into chunks."
    chunk_length = 20
    expected_chunks = [
        "This is a very long ",
        "message that needs t",
        "o be split into chu",
        "nks.",
    ]
    expected_calls = [call(chunk) for chunk in expected_chunks]

    # We patch the two helper functions within the module where they are used.
    # The return_value for the generator mock is a simple iterable (like a list).
    with (
        patch(
            "packages.utilities.general_utils.check_message_empty",
            return_value=False,
        ) as mock_check_empty,
        patch(
            "packages.utilities.general_utils.split_message_chunks",
            return_value=expected_chunks,
        ) as mock_split_chunks,
    ):

        # Act
        await utils.send_long_message(mock_ctx, long_message, chunk_length)

        # Assert
        # Check that the helpers were called as expected
        mock_check_empty.assert_called_once_with(long_message)
        mock_split_chunks.assert_called_once_with(long_message, chunk_length)

        # Check that ctx.reply was called for each chunk
        assert mock_ctx.reply.call_count == len(expected_chunks)
        mock_ctx.reply.assert_has_calls(expected_calls, any_order=False)

@pytest.mark.asyncio
async def test_send_long_message_short() -> None:
    """Tests that a short message is correctly sent as is."""
    message = "message"
    mock_ctx = AsyncMock()

    with (
        patch(
            "packages.utilities.general_utils.split_message_chunks",
            return_value=[message],
        ) as mock_split_chunks,
    ):
        await utils.send_long_message(mock_ctx, message, 2000)

    mock_split_chunks.assert_called_once_with(message, 2000)
    mock_ctx.reply.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_send_long_message_empty() -> None:
    """Tests that an error is raised when a message is empty."""
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError) as exc_info:
        await utils.send_long_message(mock_ctx, "", 10)

    assert str(exc_info.value) == "Message is empty!"

@pytest.mark.asyncio
@patch("packages.utilities.general_utils.discord.File")
async def test_send_file(mock_file: AsyncMock) -> None:
    """Test that a file is correctly sent."""
    mock_ctx = AsyncMock()

    await utils.send_file(mock_ctx, "file_name.png")

    mock_ctx.reply.assert_awaited_once_with(file=mock_file())

@pytest.mark.asyncio
async def test_send_long_messages() -> None:
    """Test that an array of long messages are correctly sent."""
    mock_ctx = AsyncMock()

    await utils.send_long_messages(mock_ctx, ["1234567890", "12345"], 5)

    expected_calls = [call("12345"), call("67890"), call("12345")]
    mock_ctx.reply.assert_has_calls(expected_calls, any_order=False)

@pytest.mark.asyncio
async def test_send_long_messages_empty() -> None:
    """Test that an array of empty long messages are not sent."""
    mock_ctx = AsyncMock()

    await utils.send_long_messages(mock_ctx, ["", "", "not empty"], 5)

    expected_calls = [call("not"), call("empty")]
    mock_ctx.reply.assert_has_calls(expected_calls, any_order=False)


@pytest.mark.asyncio
async def test_send_long_messages_file() -> None:
    """Test that an array of empty long messages are not sent."""
    mock_ctx = AsyncMock()

    fake_file_content = b"this is a fake image"
    test_file = discord.File(io.BytesIO(fake_file_content), filename="test_image.png")

    await utils.send_long_messages(
        ctx=mock_ctx,
        messages=[test_file],
        length=2000,
    )

    mock_ctx.reply.assert_awaited_once()
    mock_ctx.reply.assert_awaited_once_with(file=test_file)

@pytest.mark.asyncio
@patch("packages.utilities.general_utils.send_long_message")
async def test_send_long_messages_string(mock_send_long_message: AsyncMock) -> None:
    """Test that a long message in a string is correctly sent as a string."""
    mock_ctx = AsyncMock()

    await utils.send_long_messages(
        ctx=mock_ctx,
        messages="1 + 1 = 2",
        length=2000,
    )

    mock_send_long_message.assert_awaited_once_with(mock_ctx, "1 + 1 = 2", 2000)

@pytest.mark.parametrize(("input_object", "expected_output"), ENSURE_LIST_CASES)
def test_ensure_list(input_object: object, expected_output: list) -> None:
    """Test that ensure_list is working correctly."""
    result = utils.ensure_list(input_object)
    assert result == expected_output
