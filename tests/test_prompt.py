from typing import Dict, Any, List

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import json
import sys
import os
import discord
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from discord.ext import commands
from google.genai import Client
from google.genai.types import GenerateContentResponse, Candidate, Content, Part, FinishReason, \
    GenerateContentResponseUsageMetadata, SafetyRating, HarmCategory, HarmProbability, File, Tool, \
    ToolCodeExecution, ExecutableCode, Language, CodeExecutionResult, Blob, FileData, GoogleSearch, GroundingMetadata, \
    GroundingChunk, GroundingChunkWeb
from commands.prompt import prompt, CONFIG
from datetime import datetime, timezone
from pytest_mock import MockerFixture


@pytest.fixture
def mock_ctx(request: pytest.FixtureRequest) -> AsyncMock:
    ctx = AsyncMock(spec=commands.Context)
    ctx.message = AsyncMock()
    ctx.author = AsyncMock()
    ctx.bot = AsyncMock()
    ctx.bot.user = AsyncMock()

    ctx.bot.user.id = 12345
    ctx.message.attachments = []
    ctx.author.guild_permissions.administrator = False
    ctx.author.name = "TestUser"
    ctx.author.display_name = "TestUserDisplayName"
    ctx.author.id = 67890
    ctx.message.reference = None
    ctx.message.mentions = [ctx.bot.user]

    message_content: str = getattr(request, "param", {}).get(
        "message_content", "<@12345> Hello, world!"
    )
    has_reference: bool = getattr(request, "param", {}).get("has_reference", False)
    replied_message_content: str = getattr(request, "param", {}).get(
        "replied_message_content", "Original message content."
    )
    mentions: list = getattr(request, "param", {}).get("mentions", [ctx.bot.user])
    is_admin: bool = getattr(request, "param", {}).get("is_admin", False)

    ctx.message.content = message_content
    ctx.message.mentions = mentions
    ctx.author.guild_permissions.administrator = is_admin

    if has_reference:
        ctx.message.reference = MagicMock()
        ctx.message.reference.message_id = 98765

        mock_replied_message = MagicMock()
        mock_replied_message.content = replied_message_content
        ctx.channel.fetch_message = AsyncMock(
            return_value=mock_replied_message
        )
    else:
        ctx.message.reference = None
        ctx.channel.fetch_message = AsyncMock()

    return ctx


@pytest.fixture
def mock_file(request: pytest.FixtureRequest) -> MagicMock:
    """Creates a mock File object, with customizable attributes."""
    mock_file = MagicMock(spec=File)
    file_path = getattr(request, "param", {}).get(
        "file_path", os.path.join("temp", "uploaded_test_image.png")
    )
    mock_file.name = file_path
    mock_file.uri = getattr(request, "param", {}).get("uri", "mock_uri")
    mock_file.mime_type = getattr(request, "param", {}).get("mime_type", "image/png")
    return mock_file


@pytest.fixture
def mock_genai_client(request: pytest.FixtureRequest) -> MagicMock:
    """Creates a mock genai client and associated mocks, with customizable response."""
    mock_genai_client = MagicMock(spec=Client)
    mock_chat = AsyncMock()
    mock_genai_client.aio.chats.create.return_value = mock_chat

    params: Dict[str, Any] = getattr(request, "param", {})

    response_text: str = params.get("response_text", "Mocked response text")
    finish_reason = params.get("finish_reason", FinishReason.STOP)
    safety_ratings: List[SafetyRating] = params.get("safety_ratings", [])
    candidates_token_count: int = params.get("candidates_token_count", 5)
    prompt_token_count: int = params.get("prompt_token_count", 10)
    total_token_count: int = params.get("total_token_count", 15)
    executable_code: str = params.get("executable_code", "")
    code_execution_result: str = params.get("code_execution_result", "")
    inline_data: str = params.get("inline_data", "")
    grounding_details: List[Dict[str, str]] = params.get("grounding_details", [])

    parts = [Part(text=response_text)]
    if executable_code and code_execution_result:
        parts += [
            Part(
                executable_code=ExecutableCode(code=executable_code, language=Language('PYTHON')),
                code_execution_result=CodeExecutionResult(output=code_execution_result)
            )
        ]
    elif executable_code and inline_data:
        parts += [
            Part(
                executable_code=ExecutableCode(code=executable_code, language=Language('PYTHON')),
                inline_data=Blob(data=inline_data.encode())
            )
        ]

    grounding_metadata_obj = None
    if grounding_details:
        grounding_chunks = []
        for detail in grounding_details:
            title = detail.get("title", "Default Title")
            uri = detail.get("uri", "https://default.uri")
            grounding_chunks.append(
                GroundingChunk(web=GroundingChunkWeb(title=title, uri=uri))
            )
        if grounding_chunks:
            grounding_metadata_obj = GroundingMetadata(grounding_chunks=grounding_chunks)

    mock_response = GenerateContentResponse(
        candidates=[
            Candidate(
                content=Content(parts=parts),
                finish_reason=finish_reason,
                safety_ratings=safety_ratings,
                grounding_metadata=grounding_metadata_obj
            )
        ],
        usage_metadata=GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt_token_count,
            candidates_token_count=candidates_token_count,
            total_token_count=total_token_count,
        ),
    )
    mock_chat.send_message.return_value = mock_response
    return mock_genai_client


@pytest.fixture
def datetime_mock(mocker: MockerFixture) -> MagicMock:
    """Creates a mock datetime object for testing."""
    test_datetime = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    datetime_mock = MagicMock(wraps=test_datetime)
    datetime_mock.strftime.return_value = "Monday, January 01, 2024 12:00:00 UTC"
    mocker.patch("commands.prompt.datetime", datetime_mock)
    return datetime_mock


@pytest.fixture
def mock_temp_config(request: pytest.FixtureRequest) -> dict:
    """Provides the mock temporary configuration."""
    params: Dict[str, Any] = getattr(request, "param", {})

    uwu: bool = params.get('uwu', False)
    return {
        "model": "gemini-pro",
        "system_prompt": "You are a helpful assistant.",
        "uwu": uwu
    }


def create_mock_attachments(attachment_data: list[dict]) -> tuple[list[AsyncMock], list[MagicMock]]:
    mock_attachments = []
    mock_files = []
    for data in attachment_data:
        mock_attachment = AsyncMock(spec=discord.Attachment)
        mock_attachment.filename = data["filename"]
        mock_attachment.content_type = data["content_type"]
        mock_attachments.append(mock_attachment)

        mock_file = MagicMock(spec=File)
        mock_file_path = os.path.join("temp", f"uploaded_{data['filename']}")
        mock_file.name = mock_file_path
        mock_file.uri = f"mock_uri_{data['filename']}"
        mock_file.mime_type = data["content_type"]
        mock_files.append(mock_file)

    return mock_attachments, mock_files


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> Hello, world!"},
    ],
    indirect=["mock_ctx"],
)
async def test_prompt_basic_success(mock_ctx: AsyncMock, mock_genai_client: MagicMock, datetime_mock: MagicMock,
                                    mock_temp_config: dict):
    """Tests the basic success scenario of the prompt command with mocked datetime."""

    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.handle_attachment") as mock_handle_attachment, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("os.remove") as mock_os_remove, \
            patch("commands.prompt.datetime") as mock_datetime:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text", 2000)
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()

    mock_handle_attachment.assert_not_called()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    expected_start = "Monday, January 01, 2024 12:00:00 UTC, TestUser With Display Name TestUserDisplayName and ID 67890: "

    assert sent_prompt[0] == expected_start
    assert sent_prompt[1] == "Hello, world!"

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert kwargs['config'].system_instruction == mock_temp_config["system_prompt"]
    assert kwargs['model'] == mock_temp_config["model"]

    datetime_mock.strftime.assert_called_once_with("%A, %B %d, %Y %H:%M:%S UTC")
    mock_datetime.now.assert_called_once_with(timezone.utc)

    mock_os_remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345>"},
    ],
    indirect=["mock_ctx"],
)
async def test_prompt_empty_with_mention(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests the scenario where the prompt is empty after the bot mention."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)

        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_ctx.send.assert_called_once_with("You mentioned me or replied to me, but you didn't give me any prompt!")
    mock_genai_client.aio.chats.create.assert_not_called()
    mock_chat.send_message.assert_not_called()
    mock_ctx.typing.assert_not_called()
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()
    mock_ctx.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "Hi, Star wolf!", "mentions": []},
    ],
    indirect=["mock_ctx"],
)
async def test_no_prompt(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests the scenario where the prompt is empty after the bot mention."""
    mock_chat = mock_genai_client.aio.chats.create.return_value

    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)

        await command_func(mock_ctx)

    mock_ctx.send.assert_not_called()
    mock_genai_client.aio.chats.create.assert_not_called()
    mock_chat.send_message.assert_not_called()
    mock_ctx.typing.assert_not_called()
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()
    mock_ctx.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> Hello, world!", "has_reference": True},
    ],
    indirect=["mock_ctx"],
)
async def test_prompt_with_reply(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict,
                                 datetime_mock: MagicMock):
    """Tests the basic success scenario of the prompt command."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

    mock_ctx.channel.fetch_message.assert_called_once_with(98765)
    mock_send_long_message.assert_called_once()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    expected_start = "Monday, January 01, 2024 12:00:00 UTC, TestUser With Display Name TestUserDisplayName and ID 67890 Replied to your message, \"Original message content.\": "

    assert sent_prompt[0] == expected_start
    assert sent_prompt[1] == "Hello, world!"

    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text", 2000)
    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert kwargs['config'].system_instruction == mock_temp_config["system_prompt"]
    assert kwargs['model'] == mock_temp_config["model"]
    datetime_mock.strftime.assert_called_once_with("%A, %B %d, %Y %H:%M:%S UTC")
    mock_datetime.now.assert_called_once_with(timezone.utc)


@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345>", "has_reference": True},
    ],
    indirect=["mock_ctx"],
)
@pytest.mark.asyncio
async def test_prompt_empty_with_reply(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict,
                                       datetime_mock: MagicMock):
    """Tests the basic success scenario of the prompt command."""

    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_ctx.send.assert_called_once_with("You mentioned me or replied to me, but you didn't give me any prompt!")

    mock_genai_client.aio.chats.create.assert_not_called()
    mock_chat.send_message.assert_not_called()
    mock_ctx.typing.assert_not_called()
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()
    mock_ctx.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "The derivative of <tex>\\frac{1}{x}</tex> is <tex>-\\frac{1}{x^2}</tex>"},
    ],
    indirect=["mock_genai_client"],
)
async def test_prompt_valid_latex(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests the scenario with valid LaTeX in the prompt, including multiple renders."""
    mock_filenames = ["mocked_latex_image1.png", "mocked_latex_image2.png"]
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.render_latex", side_effect=mock_filenames) as mock_render_latex, \
            patch("commands.prompt.split_tex",
                  return_value=["The derivative of ", "<tex>\\frac{1}{x}</tex>", " is ", "<tex>-\\frac{1}{x^2}</tex>"]), \
            patch("commands.prompt.check_tex", side_effect=lambda x: x.startswith("<tex>") and x.endswith("</tex>")), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:

        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

    assert mock_render_latex.call_count == 2
    mock_render_latex.assert_has_calls([
        unittest.mock.call("<tex>\\frac{1}{x}</tex>"),
        unittest.mock.call("<tex>-\\frac{1}{x^2}</tex>")
    ])

    mock_send_long_messages.assert_called_once()

    args, kwargs = mock_send_long_messages.call_args
    sent_message_parts = args[1]

    expected_text_parts = [
        "The derivative of ",
        " is "
    ]
    file_count = 0
    text_part_index = 0

    for part in sent_message_parts:
        if isinstance(part, str):
            assert expected_text_parts[text_part_index] in part
            text_part_index += 1
        elif isinstance(part, discord.File):
            assert part.filename in mock_filenames
            file_count += 1

    assert file_count == 2
    assert text_part_index == len(expected_text_parts)

    mock_send_long_message.assert_not_called()
    mock_send_image.assert_not_called()
    assert mock_os_remove.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "Here's the LaTeX you requested: <tex>\\frac{1}{</tex>"},
    ],
    indirect=["mock_genai_client"],
)
async def test_prompt_invalid_latex(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests the scenario with invalid LaTeX in the prompt."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.render_latex", return_value=None) as mock_render_latex, \
            patch("commands.prompt.split_tex",
                  return_value=["Here's the LaTeX you requested: ", "<tex>\\frac{1}{</tex>"]), \
            patch("commands.prompt.check_tex", side_effect=lambda x: x.startswith("<tex>") and x.endswith("</tex>")), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

    mock_render_latex.assert_called_once_with("<tex>\\frac{1}{</tex>")

    mock_send_long_messages.assert_called_once()
    args, _ = mock_send_long_messages.call_args
    sent_message_parts = args[1]
    assert sent_message_parts[0] == "Here's the LaTeX you requested: "
    assert sent_message_parts[
               1] == r"<tex>\frac{1}{</tex> (Contains Invalid LaTeX Expressions)"

    mock_send_long_message.assert_not_called()
    mock_send_image.assert_not_called()
    mock_os_remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "Valid: <tex>\\frac{1}{x}</tex>, Invalid: <tex>\\frac{1}{</tex>"},
    ],
    indirect=["mock_genai_client"],
)
async def test_prompt_mixed_valid_and_invalid_latex(mock_ctx: AsyncMock, mock_genai_client: MagicMock,
                                                    mock_temp_config: dict):
    """Tests scenarios with both valid and invalid LaTeX in the same response."""

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_valid_filename = "mocked_latex_image.png"
    mock_render_latex_side_effect = [mock_valid_filename, None]
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.render_latex", side_effect=mock_render_latex_side_effect) as mock_render_latex, \
            patch("commands.prompt.split_tex",
                  return_value=["Valid: ", "<tex>\\frac{1}{x}</tex>", ", Invalid: ", "<tex>\\frac{1}{</tex>"]), \
            patch("commands.prompt.check_tex", side_effect=lambda x: x.startswith("<tex>") and x.endswith("</tex>")), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:

        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

    assert mock_render_latex.call_count == 2
    mock_render_latex.assert_has_calls([
        unittest.mock.call("<tex>\\frac{1}{x}</tex>"),
        unittest.mock.call("<tex>\\frac{1}{</tex>")
    ])

    mock_send_long_messages.assert_called_once()
    args, _ = mock_send_long_messages.call_args
    sent_message_parts = args[1]

    expected_text_parts = [
        "Valid: ",
        ", Invalid: ",
        "<tex>\\frac{1}{</tex> (Contains Invalid LaTeX Expressions)"
    ]

    file_count = 0
    text_part_index = 0
    for part in sent_message_parts:
        if isinstance(part, str):
            assert expected_text_parts[text_part_index] in part
            text_part_index += 1
        elif isinstance(part, discord.File):
            assert part.filename == mock_valid_filename
            file_count += 1
        else:
            pytest.fail(f"Unexpected part type: {type(part)}")

    assert file_count == 1
    assert text_part_index == len(expected_text_parts)

    mock_send_long_message.assert_not_called()
    mock_send_image.assert_not_called()
    mock_os_remove.assert_called_once_with(mock_valid_filename)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> {clear}", "is_admin": True}
    ],
    indirect=["mock_ctx"],
)
async def test_clear_admin(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests the clear success scenario of the prompt command."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch('commands.prompt.memory.clear') as mock_memory_clear:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_not_called()
    mock_chat.send_message.assert_not_called()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()
    mock_ctx.reply.assert_called_once_with("Alright, I have cleared my context. What are we gonna talk about?")
    mock_memory_clear.assert_called_once()
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> {clear}", "is_admin": False}
    ],
    indirect=["mock_ctx"],
)
async def test_clear_no_admin(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests the fail clear scenario of the prompt command without admin."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch('commands.prompt.memory.clear') as mock_memory_clear:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_not_called()
    mock_chat.send_message.assert_not_called()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()
    mock_ctx.reply.assert_called_once_with("You don't have the necessary permissions for this!", ephemeral=True)
    mock_memory_clear.assert_not_called()
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
async def test_memory_load_empty(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Test memory loading behavior when the memory list is initially empty."""
    mock_loaded_memory = "This is a test memory string."

    with patch("commands.prompt.memory", []), \
            patch("commands.prompt.load_memory", return_value=mock_loaded_memory) as mock_load_memory, \
            patch("commands.prompt.send_long_message"), \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_load_memory.assert_called_once()
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert sent_prompt[0] == f"This is the memory you saved: {mock_loaded_memory}"


@pytest.mark.asyncio
async def test_memory_load_not_empty(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Test that load_memory is NOT called when the memory list is NOT empty."""
    with patch("commands.prompt.memory", ["some", "existing", "memory"]), \
            patch("commands.prompt.load_memory") as mock_load_memory, \
            patch("commands.prompt.send_long_message"), \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_load_memory.assert_not_called()
    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert not sent_prompt[0].startswith("This is the memory you saved:")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "finish_reason": FinishReason.SAFETY,
            "safety_ratings": [
                SafetyRating(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    probability=HarmProbability.HIGH,
                )
            ],
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_single_safety_blocked(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Test a single blocked safety rating."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.memory", []), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.SAFETY_SETTING", "BLOCK_MEDIUM_AND_ABOVE"):
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_ctx.reply.assert_called_once_with("This response was blocked due to Harassment", ephemeral=True)

    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "finish_reason": FinishReason.SAFETY,
            "safety_ratings": [
                SafetyRating(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    probability=HarmProbability.MEDIUM,
                ),
                SafetyRating(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    probability=HarmProbability.HIGH,
                ),
            ],
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_multiple_safety_blocked(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Test multiple blocked safety ratings."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.memory", []), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.SAFETY_SETTING", "BLOCK_MEDIUM_AND_ABOVE"):
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.reply.assert_called_once_with("This response was blocked due to Harassment, Hate Speech", ephemeral=True)
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "safety_ratings": [
                SafetyRating(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    probability=HarmProbability.LOW,
                ),
            ],
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_not_detected_safety_threshold(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Test safety threshold below BLOCK_ONLY_HIGH."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.memory", []), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.load_config",
                  return_value={**CONFIG, "HarmBlockThreshold": "BLOCK_MEDIUM_AND_ABOVE"}):
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.reply.assert_not_called()
    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text", 2000)
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_file",
    [
        {
            "file_path": os.path.join("temp", "uploaded_test_image.png"),
            "uri": "mock_uri",
            "mime_type": "image/png",
        }
    ],
    indirect=["mock_file"],
)
async def test_single_attachment_success(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_file: MagicMock,
                                         mock_temp_config: dict):
    """Tests a single attachment, successful upload."""
    attachment_data = [
        {"filename": "test_image.png", "content_type": "image/png"},
    ]
    mock_attachments, mock_files = create_mock_attachments(attachment_data)
    mock_ctx.message.attachments = mock_attachments
    mock_attachment = mock_attachments[0]

    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.handle_attachment",
                  return_value=([mock_file.name], [mock_file])) as mock_handle_attachment, \
            patch("commands.prompt.wait_for_file_active") as mock_wait_for_file_active, \
            patch("commands.prompt.memory", []), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_handle_attachment.assert_called_once_with(mock_attachment, mock_genai_client)
    mock_wait_for_file_active.assert_called_once_with(mock_file)

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert sent_prompt[2].file_data.file_uri == "mock_uri"
    assert sent_prompt[2].file_data.mime_type == "image/png"

    mock_os_remove.assert_called_once_with(mock_file.name)

    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text", 2000)
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_attachments_success(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests multiple attachments, all successful."""
    attachment_data = [
        {"filename": "image1.png", "content_type": "image/png"},
        {"filename": "document.pdf", "content_type": "application/pdf"},
    ]
    mock_attachments, mock_files = create_mock_attachments(attachment_data)
    mock_ctx.message.attachments = mock_attachments

    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.handle_attachment",
                  side_effect=[([mock_file.name], [mock_file]) for mock_file in mock_files]) as mock_handle_attachment, \
            patch("commands.prompt.wait_for_file_active") as mock_wait_for_file_active, \
            patch("commands.prompt.memory", []), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_handle_attachment.assert_has_calls([
        call(mock_attachment, mock_genai_client) for mock_attachment in mock_attachments
    ])

    mock_wait_for_file_active.assert_has_calls([
        call(mock_file) for mock_file in mock_files
    ])

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert sent_prompt[1] == "Hello, world!"
    assert sent_prompt[2].file_data.file_uri == "mock_uri_image1.png"
    assert sent_prompt[2].file_data.mime_type == "image/png"
    assert sent_prompt[3].file_data.file_uri == "mock_uri_document.pdf"
    assert sent_prompt[3].file_data.mime_type == "application/pdf"

    mock_os_remove.assert_has_calls([
        call(mock_file.name) for mock_file in mock_files
    ], any_order=True)

    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text", 2000)
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
async def test_attachment_failure(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Tests a single attachment, but handle_attachment fails."""
    mock_attachment = AsyncMock(spec=discord.Attachment)
    mock_attachment.filename = "failed_image.png"
    mock_attachment.content_type = "image/png"
    mock_ctx.message.attachments = [mock_attachment]

    error_message = "Yes"
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.handle_attachment", return_value=Exception(error_message)) as mock_handle_attachment, \
            patch("commands.prompt.wait_for_file_active") as mock_wait_for_file_active, \
            patch("commands.prompt.memory", []), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_handle_attachment.assert_called_once_with(mock_attachment, mock_genai_client)
    mock_wait_for_file_active.assert_not_called()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert sent_prompt[1] == "Hello, world!"
    assert len(sent_prompt) == 2

    mock_send_long_message.assert_any_call(mock_ctx,
                                           f"Error: Failed to upload attachment(s). Continuing as if the files are not uploaded. Error: `{error_message}`.",
                                           2000)
    mock_send_long_message.assert_called_with(mock_ctx, "Mocked response text", 2000)
    mock_os_remove.assert_not_called()

    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "executable_code": "print('Hello, World!')",
            "code_execution_result": "Hello, World!"
        }
    ],
    indirect=["mock_genai_client"],
)
async def test_handle_executable_code_and_code_execution_result(mock_ctx: AsyncMock, mock_genai_client: MagicMock,
                                                                mock_temp_config: dict):
    tool = Tool(code_execution=ToolCodeExecution())
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        command_func = prompt([tool], mock_genai_client)
        await command_func(mock_ctx)

    mock_send_long_message.assert_has_calls([
        call(mock_ctx, 'Mocked response text', 2000),
        call(mock_ctx, "Code:\n```python\nprint('Hello, World!')\n```", 2000),
        call(mock_ctx, 'Output:\n```\nHello, World!\n```', 2000)
    ])

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert 'config' in kwargs
    assert hasattr(kwargs['config'], 'tools')
    assert kwargs['config'].tools == [tool]
    assert kwargs['config'].automatic_function_calling.maximum_remote_calls == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "executable_code": "print('Some Matplotlib Magic!')",
            "inline_data": "random image byte data hehhe"
        }
    ],
    indirect=["mock_genai_client"],
)
async def test_handle_executable_code_and_inline_data(mock_ctx: AsyncMock, mock_genai_client: MagicMock,
                                                      mock_temp_config: dict,
                                                      mock_file):
    tool = Tool(code_execution=ToolCodeExecution())
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.memory", []), \
            patch("os.remove") as mock_os_remove, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mock_file = mocked_open.return_value.__enter__.return_value
        mock_file.write.return_value = None

        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        command_func = prompt([tool], mock_genai_client)
        await command_func(mock_ctx)

    mock_send_long_message.assert_has_calls([
        call(mock_ctx, 'Mocked response text', 2000),
        call(mock_ctx, "Code:\n```python\nprint('Some Matplotlib Magic!')\n```", 2000),
    ])
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_called_once()

    mock_file.write.assert_called_once_with("random image byte data hehhe".encode())
    mock_os_remove.assert_called_once()

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert kwargs['config'].tools == [tool]
    assert kwargs['config'].automatic_function_calling.maximum_remote_calls == 5

@pytest.mark.parametrize("mock_genai_client", [
    {
        "grounding_details": [
            {"title": "Source 1", "uri": "https://source1.com"},
            {"title": "Source 2 (Blog)", "uri": "https://blog.source2.com/article"}
        ]
    }
], indirect=True)
@pytest.mark.asyncio
async def test_grounding_markdown(mock_ctx: AsyncMock, mock_genai_client: MagicMock,
                                  mock_temp_config: dict):
    tool = Tool(google_search=GoogleSearch())
    source = ("## Grounding Sources:\n\n"
    "- [Source 1](https://source1.com)\n"
    "- [Source 2 (Blog)](https://blog.source2.com/article)")

    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("commands.prompt.create_grounding_markdown", return_value=source) as mock_grounding, \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        command_func = prompt([tool], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_candidate = mock_chat.send_message.return_value.candidates

    mock_grounding.assert_called_once_with(mock_candidate)

    mock_send_long_message.assert_called_once_with(mock_ctx, f'Mocked response text\n{source}', 2000)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> A youtube link! https://www.youtube.com/watch?v=t5XOXQqsTvM"}
    ],
    indirect=["mock_ctx"],
)
async def test_youtube_processing(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict,
                                  datetime_mock: MagicMock):
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message"), \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]

    assert (sent_prompt[0] ==
            'Monday, January 01, 2024 12:00:00 UTC, TestUser With Display Name TestUserDisplayName and ID 67890: ')
    assert sent_prompt[1] == 'A youtube link! '
    assert sent_prompt[2] == Part(file_data=FileData(file_uri='https://www.youtube.com/watch?v=t5XOXQqsTvM'))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "finish_reason": FinishReason.MALFORMED_FUNCTION_CALL,
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_malformed_function_call(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict):
    """Test multiple blocked safety ratings."""
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages") as mock_send_long_messages, \
            patch("commands.prompt.send_image") as mock_send_image, \
            patch("commands.prompt.memory", []), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.reply.assert_called_once_with("Seems like my function calling tool is malformed. Try again!")
    mock_send_long_message.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "<thought>Big Thinking 🤔</thought>\nSo, I thought."},
    ],
    indirect=["mock_genai_client"],
)
async def test_thought(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict, datetime_mock):
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime, \
            patch("commands.prompt.save_temp_config") as mock_save_temp_config:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_send_long_message.assert_called_once_with(mock_ctx, "\nSo, I thought.\n(This reply have a thought)", 2000)
    mock_save_temp_config.assert_called_once_with(thought=["<thought>Big Thinking 🤔</thought>"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "<store>Big Secret TeeHee</store>\nYou'll never know!"},
    ],
    indirect=["mock_genai_client"],
)
@pytest.mark.asyncio
async def test_secret(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict, datetime_mock):
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime, \
            patch("commands.prompt.save_temp_config") as mock_save_temp_config:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_send_long_message.assert_called_once_with(mock_ctx, "\nYou'll never know!", 2000)
    mock_save_temp_config.assert_called_once_with(secret=["<store>Big Secret TeeHee</store>"])

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_temp_config",
    [
        {'uwu': True},
    ],
    indirect=["mock_temp_config"],
)
async def test_uwu(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict, datetime_mock):
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime, \
            patch("commands.prompt.save_temp_config"), \
            patch("commands.prompt.Uwuifier.uwuify_sentence", return_value="Mocked response text :3") as mock_uwuify_sentence:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_uwuify_sentence.assert_called_once_with("Mocked response text")
    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text :3", 2000)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "finish_reason": FinishReason.MAX_TOKENS,
        },
    ],
    indirect=["mock_genai_client"],
)
@pytest.mark.asyncio
async def test_finish_reason_max_tokens(mock_ctx: AsyncMock, mock_genai_client: MagicMock, mock_temp_config: dict, datetime_mock):
    with patch("commands.prompt.load_memory", return_value=None), \
            patch("commands.prompt.send_long_message") as mock_send_long_message, \
            patch("commands.prompt.send_long_messages"), \
            patch("commands.prompt.send_image"), \
            patch("commands.prompt.memory", []), \
            patch("os.remove"), \
            patch("builtins.open", new_callable=MagicMock) as mocked_open, \
            patch("commands.prompt.datetime") as mock_datetime:
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_temp_config)
        mock_datetime.now.return_value = datetime_mock

        command_func = prompt([], mock_genai_client)
        await command_func(mock_ctx)

    mock_send_long_message.assert_called_once_with(mock_ctx, "Mocked response text\n(Response May Be Cut Off)", 2000)


@pytest.mark.asyncio
async def test_context():
    pass


@pytest.mark.asyncio
async def test_context_empty():
    pass
