from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import discord
import pytest
import regex
from discord.ext import commands
from google.genai import Client, errors
from google.genai.types import (
    AutomaticFunctionCallingConfig,
    Blob,
    Candidate,
    CodeExecutionResult,
    Content,
    ExecutableCode,
    File,
    FileData,
    FinishReason,
    GenerateContentConfig,
    GenerateContentResponse,
    GenerateContentResponseUsageMetadata,
    GoogleSearch,
    GroundingChunk,
    GroundingChunkWeb,
    GroundingMetadata,
    HarmBlockThreshold,
    HarmCategory,
    HarmProbability,
    Language,
    Part,
    SafetyRating,
    SafetySetting,
    Tool,
    ToolCodeExecution,
)
from requests import Response

from commands.prompt import prompt
from packages.maps import YOUTUBE_PATTERN

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture
    # from anyio.streams.file import FileWriteStream # Example type hint if needed

# <<<--- Rest of existing fixtures (mock_ctx, mock_file, etc.) --->>>

DEFAULT_RENDER_LATEX_CONFIG = {"return_value": None}
DEFAULT_SPLIT_TEX_CONFIG = {"side_effect": lambda t: ([t], False)}
DEFAULT_CHECK_TEX_CONFIG = {"return_value": False}
DEFAULT_HANDLE_ATTACHMENT_CONFIG = {}
DEFAULT_GET_MEMORY_CONFIG = {"return_value": []}
DEFAULT_CREATE_GROUNDING_MARKDOWN_CONFIG = {"return_value": ""}
DEFAULT_LOAD_MEMORY_CONFIG = {"return_value": None}
DEFAULT_UWUIFY_CONFIG = {"side_effect": lambda s: s}
DEFAULT_MOCK_RESPONSE_TEXT = "Mocked response text"
DEFAULT_EMPTY_PROMPT_MESSAGE = ("You mentioned me or replied to me, "
                                "but you didn't give me any prompt!")
DEFAULT_MODEL = "gemini-pro"
DEFAULT_CHAR_LIMIT = 2000

@pytest.fixture
def mock_ctx(request: pytest.FixtureRequest) -> AsyncMock:
    """Mock the discord.commands,Context object."""
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
        "message_content", "<@12345> Hello, world!",
    )
    has_reference: bool = getattr(request, "param", {}).get("has_reference", False)
    replied_message_content: str = getattr(request, "param", {}).get(
        "replied_message_content", "Original message content.",
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
            return_value=mock_replied_message,
        )
    else:
        ctx.message.reference = None
        ctx.channel.fetch_message = AsyncMock()

    return ctx


@pytest.fixture
def mock_file(request: pytest.FixtureRequest) -> MagicMock:
    """Create a mock File object, with customizable attributes."""
    mock_file = MagicMock(spec=File)
    file_path = getattr(request, "param", {}).get(
        "file_path", Path("temp") / "uploaded_test_image.png",
    )
    mock_file.name = file_path
    mock_file.uri = getattr(request, "param", {}).get("uri", "mock_uri")
    mock_file.mime_type = getattr(request, "param", {}).get("mime_type", "image/png")
    return mock_file


@pytest.fixture
def mock_genai_client(request: pytest.FixtureRequest) -> MagicMock:
    """Create a mock genai client and associated mocks, with customizable response."""
    mock_genai_client = MagicMock(spec=Client)
    mock_chat = AsyncMock()
    mock_genai_client.aio.chats.create.return_value = mock_chat

    params: dict[str, Any] = getattr(request, "param", {})

    response_text: str = params.get("response_text", DEFAULT_MOCK_RESPONSE_TEXT)
    finish_reason = params.get("finish_reason", FinishReason.STOP)
    safety_ratings: list[SafetyRating] = params.get("safety_ratings", [])
    candidates_token_count: int = params.get("candidates_token_count", 5)
    prompt_token_count: int = params.get("prompt_token_count", 10)
    total_token_count: int = params.get("total_token_count", 15)
    executable_code: str = params.get("executable_code", "")
    code_execution_result: str = params.get("code_execution_result", "")
    inline_data: str = params.get("inline_data", "")
    grounding_details: list[dict[str, str]] = params.get("grounding_details", [])
    curated_history: list = params.get("curated_history", [])

    parts = [Part(text=response_text)]
    if executable_code and code_execution_result:
        parts += [
            Part(
                executable_code=ExecutableCode(
                    code=executable_code,
                    language=Language("PYTHON"),
                ),
                code_execution_result=CodeExecutionResult(output=code_execution_result),
            ),
        ]
    elif executable_code and inline_data:
        parts += [
            Part(
                executable_code=ExecutableCode(
                    code=executable_code, language=Language("PYTHON"),
                ),
                inline_data=Blob(data=inline_data.encode()),
            ),
        ]

    grounding_metadata_obj = None
    if grounding_details:
        grounding_chunks = []
        for detail in grounding_details:
            title = detail.get("title", "Default Title")
            uri = detail.get("uri", "https://default.uri")
            grounding_chunks.append(
                GroundingChunk(web=GroundingChunkWeb(title=title, uri=uri)),
            )
        if grounding_chunks:
            grounding_metadata_obj = GroundingMetadata(
                grounding_chunks=grounding_chunks,
            )

    mock_response = GenerateContentResponse(
        candidates=[
            Candidate(
                content=Content(parts=parts),
                finish_reason=finish_reason,
                safety_ratings=safety_ratings,
                grounding_metadata=grounding_metadata_obj,
            ),
        ],
        usage_metadata=GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt_token_count,
            candidates_token_count=candidates_token_count,
            total_token_count=total_token_count,
        ),
    )
    mock_chat.send_message.return_value = mock_response
    mock_chat._curated_history = curated_history
    return mock_genai_client


@pytest.fixture
def datetime_mock(mocker: MockerFixture) -> MagicMock:
    """Create a mock object for datetime object."""
    test_datetime = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    datetime_mock = MagicMock(wraps=test_datetime)
    datetime_mock.strftime.return_value = "Monday, January 01, 2024 12:00:00 UTC"
    datetime_mock.now.return_value = datetime_mock
    mocker.patch("commands.prompt.datetime", datetime_mock)
    return datetime_mock


@pytest.fixture
def mock_temp_config(request: pytest.FixtureRequest) -> dict:
    """Create a mock object for temporary configuration."""
    params: dict[str, Any] = getattr(request, "param", {})

    uwu: bool = params.get("uwu", False)
    model: str = params.get("model", DEFAULT_MODEL)
    return {
        "model": model,
        "system_prompt": "You are a helpful assistant.",
        "uwu": uwu,
    }


@pytest.fixture(autouse=True)
def mock_load_config() -> Generator[None, None, None]:
    """Patch the config file."""
    with patch("packages.utilities.prompt_utils.load_config") as mock:
        mock.return_value = {
            "GeminiAPIKey": "test_api_key",
            "DiscordToken": "test_token",
            "OwnerID": "12345",
            "WolframAPI": "test_wolfram",
            "HarmBlockThreshold": "BLOCK_MEDIUM_AND_ABOVE",
            "Temperature": 1,
        }
        yield


@pytest.fixture
def mock_common_dependencies(
        mocker: MockerFixture,
        mock_temp_config: dict,
        request: pytest.FixtureRequest,
) -> dict:
    """Mock common dependencies used across prompt tests.

    Allows overrides via request.param. Uses anyio.open_file mock.
    """
    params_override = getattr(request, "param", {})

    # --- Get specific configs from params_override or use defaults ---
    render_latex_config = params_override.get(
        "render_latex_config",
        DEFAULT_RENDER_LATEX_CONFIG,
    )
    split_tex_config = params_override.get(
        "split_tex_config",
        DEFAULT_SPLIT_TEX_CONFIG,
    )
    check_tex_config = params_override.get(
        "check_tex_config",
        DEFAULT_CHECK_TEX_CONFIG,
    )
    handle_attachment_config = params_override.get(
        "handle_attachment_config",
        DEFAULT_HANDLE_ATTACHMENT_CONFIG,
    )
    get_memory_config = params_override.get(
        "get_memory_config",
        DEFAULT_GET_MEMORY_CONFIG,
    )
    load_memory_config = params_override.get(
        "load_memory_config",
        DEFAULT_LOAD_MEMORY_CONFIG,
    )
    create_grounding_markdown_config = params_override.get(
        "create_grounding_markdown_config",
        DEFAULT_CREATE_GROUNDING_MARKDOWN_CONFIG,
    )
    uwuify_config = params_override.get("uwuify_config", DEFAULT_UWUIFY_CONFIG)

    # --- Mock setup for anyio.open_file ---
    # Mock for the async file handle itself
    mock_async_file_handle = AsyncMock()
    mock_async_file_handle.write = AsyncMock()

    # Mock for the async context manager returned by anyio.open_file
    mock_open_context_manager = AsyncMock()
    mock_open_context_manager.__aenter__.return_value = mock_async_file_handle
    mock_open_context_manager.__aexit__.return_value = None

    # Patch anyio.open_file to return the context manager mock
    # IMPORTANT: Adjust "commands.prompt.anyio.open_file" if your import differs!
    mock_anyio_open_patch = mocker.patch(
        "packages.utilities.prompt_utils.anyio.open_file",
        return_value=mock_open_context_manager,
    )

    return {
        "load_memory": mocker.patch(
            "commands.prompt.load_memory",
            **load_memory_config,
        ),
        "save_memory": mocker.patch("commands.prompt.save_memory"),
        "clear_memory": mocker.patch("commands.prompt.clear_memory"),
        "get_memory": mocker.patch(
            "commands.prompt.get_memory",
            **get_memory_config,
        ),
        "send_long_message_prompt_utils": mocker.patch(
            "packages.utilities.prompt_utils.send_long_message",
        ),
        "send_long_message": mocker.patch(
            "commands.prompt.send_long_message",
        ),
        "send_long_messages": mocker.patch(
            "packages.utilities.prompt_utils.send_long_messages",
        ),
        "send_image": mocker.patch("packages.utilities.prompt_utils.send_image"),
        "handle_attachment": mocker.patch(
            "packages.utilities.prompt_utils.handle_attachment",
            **handle_attachment_config,
        ),
        "wait_for_file_active": mocker.patch(
            "packages.utilities.prompt_utils.wait_for_file_active",
        ),
        "render_latex": mocker.patch(
            "packages.utilities.prompt_utils.render_latex",
            **render_latex_config,
        ),
        "split_tex": mocker.patch(
            "packages.utilities.prompt_utils.split_tex",
            **split_tex_config,
        ),
        "check_tex": mocker.patch(
            "packages.utilities.prompt_utils.check_tex",
            **check_tex_config,
        ),
        "os_remove": mocker.patch("os.remove"),
        "uwuify": mocker.patch(
            "packages.utilities.prompt_utils.Uwuifier.uwuify_sentence",
            **uwuify_config,
        ),
        "create_grounding_markdown": mocker.patch(
            "packages.utilities.prompt_utils.create_grounding_markdown",
            **create_grounding_markdown_config,
        ),
        "save_temp_config": mocker.patch(
            "packages.utilities.prompt_utils.save_temp_config",
        ),
        "mock_read_temp_config": mocker.patch(
            "packages.utilities.prompt_utils.read_temp_config",
            return_value=mock_temp_config,
        ),
        # Provide the anyio mocks for test assertions
        "mock_anyio_open": mock_anyio_open_patch,
        "mock_async_file_handle": mock_async_file_handle,
        "mock_open": mocker.patch(
            "builtins.open",
            mocker.mock_open(read_data=b"a new file"),
        ),
    }

# <<<--- Rest of existing helper functions (create_mock_attachments, etc.) --->>>

def create_mock_attachments(
        attachment_data: list[dict],
) -> tuple[list[AsyncMock], list[MagicMock]]:
    """Create a mock attachment object."""
    mock_attachments = []
    mock_files = []
    for data in attachment_data:
        mock_attachment = AsyncMock(spec=discord.Attachment)
        mock_attachment.filename = data["filename"]
        mock_attachment.content_type = data["content_type"]
        mock_attachments.append(mock_attachment)

        mock_file = MagicMock(spec=File)
        mock_file_path = Path("temp") / f"uploaded_{data['filename']}"
        mock_file.name = mock_file_path
        mock_file.uri = f"mock_uri_{data['filename']}"
        mock_file.mime_type = data["content_type"]
        mock_files.append(mock_file)

    return mock_attachments, mock_files


def generate_safety_config(safety_setting: HarmBlockThreshold) -> list[SafetySetting]:
    """Generate a safety template config for Gemini."""
    return [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=safety_setting,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=safety_setting,
        ),
    ]


def generate_config_normal(safety_setting: HarmBlockThreshold) -> GenerateContentConfig:
    """Generate a template config for an image generation model."""
    safety = generate_safety_config(safety_setting)
    return GenerateContentConfig(
        system_instruction="You are a helpful assistant.",
        temperature=1,
        safety_settings=safety,
        automatic_function_calling=AutomaticFunctionCallingConfig(
            maximum_remote_calls=5,
        ),
        tools=[],
    )

def generate_config_image(safety_setting: HarmBlockThreshold) -> GenerateContentConfig:
    """Generate a template config for a normal model (non image generating)."""
    safety = generate_safety_config(safety_setting)
    return GenerateContentConfig(
        system_instruction=None,
        temperature=1,
        safety_settings=safety,
        automatic_function_calling=None,
        tools=None,
        response_modalities=["Text", "Image"],
    )


def assert_base_nothing(
        mock_genai_client: MagicMock,
        mock_chat: MagicMock,
        mock_send_long_message_prompt_utils: MagicMock,
        mock_send_long_messages: MagicMock,
        mock_send_image: MagicMock,
) -> None:
    """Implement base assertions for tests expecting no action."""
    mock_genai_client.aio.chats.create.assert_not_called()
    mock_chat.send_message.assert_not_called()
    mock_send_long_message_prompt_utils.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


def assert_when_error(
    mock_genai_client: MagicMock,
    mock_chat: MagicMock,
    mock_ctx: MagicMock,
    mock_send_long_message_prompt_utils: MagicMock,
    mock_send_long_messages: MagicMock,
    mock_send_image: MagicMock,
) -> None:
    """Assert the correct things happen when error."""
    assert_base_nothing(
        mock_genai_client,
        mock_chat,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )
    mock_ctx.reply.assert_not_called()
    mock_ctx.typing.assert_not_called()


def assert_not_needed(
    mock_genai_client: MagicMock,
    mock_chat: MagicMock,
    mock_ctx: MagicMock,
    mock_send_long_message_prompt_utils: MagicMock,
    mock_send_long_messages: MagicMock,
    mock_send_image: MagicMock,
) -> None:
    """Assert that nothing is done."""
    assert_base_nothing(
        mock_genai_client,
        mock_chat,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )
    mock_ctx.typing.assert_called_once()


def assert_not_needed_with_discord_typing(
    mock_genai_client: MagicMock,
    mock_chat: MagicMock,
    mock_ctx: MagicMock,
    mock_send_long_message_prompt_utils: MagicMock,
    mock_send_long_messages: MagicMock,
    mock_send_image: MagicMock,
) -> None:
    """Assert that nothing will happen."""
    assert_base_nothing(
        mock_genai_client,
        mock_chat,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()



def assert_datetime(dt_mock_object: MagicMock) -> None:
    """Assert that the datetime is valid."""
    dt_mock_object.strftime.assert_called_once_with("%A, %B %d, %Y %H:%M:%S UTC")
    dt_mock_object.now.assert_called_once_with(timezone.utc)


def assert_basic_success(
    mock_genai_client: MagicMock,
    mock_chat: MagicMock,
    mock_ctx: MagicMock,
) -> None:
    """Assert the creation of the chat."""
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

def assert_sent_simple_response(
    mock_send_long_message_prompt_utils: MagicMock,
    mock_send_long_messages: MagicMock,
    mock_send_image: MagicMock,
    mock_ctx: AsyncMock,
    expected_text: str,
    expected_char_limit: int = DEFAULT_CHAR_LIMIT,
) ->  None:
    """Assert a single, simple text response was sent."""
    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        expected_text,
        expected_char_limit,
    )
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


def assert_safety_blocked(
    mock_ctx: AsyncMock,
    mock_send_long_message_prompt_utils: MagicMock,
    mock_send_long_messages: MagicMock,
    mock_send_image: MagicMock,
    expected_reason_text: str,
) -> None:
    """Assert the response was blocked due to safety and the correct reply was sent."""
    mock_ctx.reply.assert_called_once_with(
        f"This response was blocked due to {expected_reason_text}",
        ephemeral=True,
    )
    mock_send_long_message_prompt_utils.assert_not_called()
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


def assert_chats_create_args(
    mock_genai_client: MagicMock,
    expected_config: GenerateContentConfig,
    expected_model: str,
    expected_history: list | None = None,
) -> None:
    """Assert the arguments passed to genai_client.aio.chats.create."""
    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert kwargs.get("model") == expected_model
    assert kwargs.get("config") == expected_config
    assert kwargs.get("history") == expected_history


def assert_tools(kwargs: dict, tool: Tool, max_call: int = 5) -> None:
    """Assert the tools are valid."""
    assert "config" in kwargs
    assert kwargs["config"].tools == [tool]
    assert kwargs["config"].tools == [tool]
    assert kwargs["config"].automatic_function_calling.maximum_remote_calls == max_call

# <<<--- Start of existing tests --->>>

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> Hello, world!"},
    ],
    indirect=["mock_ctx"],
)
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"curated_history": ["Mock memory"]},
    ],
    indirect=["mock_genai_client"],
)
async def test_prompt_basic_success(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    datetime_mock: MagicMock,
    mock_temp_config: dict,
    mock_common_dependencies: dict,
) -> None:
    """Tests the basic success scenario using the mock fixture."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    # Access mocks through the dictionary
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_handle_attachment = mock_common_dependencies["handle_attachment"]
    mock_os_remove = mock_common_dependencies["os_remove"]
    mock_save_memory = mock_common_dependencies["save_memory"]

    expected_config = generate_config_normal(HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)

    mock_genai_client.aio.chats.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        config=expected_config,
    )
    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.send.assert_not_called()

    expected_timestamp = "Monday, January 01, 2024 12:00:00 UTC"
    expected_user = "TestUser With Display Name TestUserDisplayName and ID 67890"

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    expected_start = f"{expected_timestamp}, {expected_user}: "
    assert sent_prompt[0] == expected_start
    assert sent_prompt[1] == "Hello, world!"

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert kwargs["config"].system_instruction == mock_temp_config["system_prompt"]
    assert kwargs["model"] == mock_temp_config["model"]

    assert_datetime(datetime_mock)
    assert_sent_simple_response(
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
        mock_ctx,
        DEFAULT_MOCK_RESPONSE_TEXT,
    )
    assert_chats_create_args(
        mock_genai_client,
        expected_config=expected_config,
        expected_model=mock_temp_config["model"],
    )
    mock_os_remove.assert_not_called()
    mock_handle_attachment.assert_not_called()
    mock_save_memory.assert_called_once_with(["Mock memory"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345>"},
    ],
    indirect=["mock_ctx"],
)
async def test_prompt_empty_with_mention(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
)  -> None:
    """Tests the scenario where the prompt is empty after the bot mention."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_ctx.send.assert_called_once_with(DEFAULT_EMPTY_PROMPT_MESSAGE)
    assert_when_error(
        mock_genai_client,
        mock_chat,
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "Hi, Star wolf!", "mentions": []},
    ],
    indirect=["mock_ctx"],
)
async def test_no_prompt(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Tests the scenario where the prompt is empty after the bot mention."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]


    mock_ctx.send.assert_not_called()
    assert_when_error(
        mock_genai_client,
        mock_chat,
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> Hello, world!", "has_reference": True},
    ],
    indirect=["mock_ctx"],
)
async def test_prompt_with_reply(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_temp_config: dict,
    datetime_mock: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Tests the basic success scenario of the prompt command."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_timestamp = "Monday, January 01, 2024 12:00:00 UTC"
    expected_user = "TestUser With Display Name TestUserDisplayName and ID 67890"
    expected_reply = '"Original message content."'

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    mock_chat = mock_genai_client.aio.chats.create.return_value

    assert_basic_success(mock_genai_client, mock_chat, mock_ctx)

    mock_ctx.channel.fetch_message.assert_called_once_with(98765)
    mock_send_long_message_prompt_utils.assert_called_once()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    expected_start = (f"{expected_timestamp}, "
                      f"{expected_user} Replied to your message, "
                      f"{expected_reply}: ")

    assert sent_prompt[0] == expected_start
    assert sent_prompt[1] == "Hello, world!"

    assert_sent_simple_response(
        mock_send_long_message_prompt_utils, mock_send_long_messages, mock_send_image,
        mock_ctx, DEFAULT_MOCK_RESPONSE_TEXT,
    )

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert kwargs["config"].system_instruction == mock_temp_config["system_prompt"]
    assert kwargs["model"] == mock_temp_config["model"]
    datetime_mock.strftime.assert_called_once_with("%A, %B %d, %Y %H:%M:%S UTC")
    datetime_mock.now.assert_called_once_with(timezone.utc)


@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345>", "has_reference": True},
    ],
    indirect=["mock_ctx"],
)
@pytest.mark.asyncio
async def test_prompt_empty_with_reply(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Tests the empty reply success scenario of the prompt command."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_ctx.send.assert_called_once_with(DEFAULT_EMPTY_PROMPT_MESSAGE)

    assert_when_error(
        mock_genai_client,
        mock_chat,
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )



@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "response_text": "The derivative of "
                             "<tex>\\frac{1}{x}</tex> "
                             "is <tex>-\\frac{1}{x^2}</tex>",
        },
    ],
    indirect=["mock_genai_client"],
)
@pytest.mark.parametrize(
    "mock_common_dependencies",
    [
        {
            "render_latex_config": {
                "side_effect": [
                    "mocked_latex_image1.png",
                    "mocked_latex_image2.png",
                ],
            },
            "split_tex_config": {
                "return_value": ([
                    "The derivative of ",
                    "<tex>\\frac{1}{x}</tex>",
                    " is ",
                    "<tex>-\\frac{1}{x^2}</tex>",
                ], True),
            },
            "check_tex_config": {
                "side_effect": lambda x: x.startswith("<tex>") and x.endswith("</tex>"),
            },
        },
    ],
    indirect=["mock_common_dependencies"],
)
async def test_prompt_valid_latex(
        mock_ctx: AsyncMock,
        mock_genai_client: MagicMock,
        mock_common_dependencies: MagicMock,
) -> None:
    """Tests the scenario with valid LaTeX in the prompt, using parametrized fixture."""
    mock_filenames = ["mocked_latex_image1.png", "mocked_latex_image2.png"]

    # Access mocks (they are already configured correctly by the fixture)
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_os_remove = mock_common_dependencies["os_remove"]
    mock_render_latex = mock_common_dependencies["render_latex"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_file_counts = 2

    mock_chat = mock_genai_client.aio.chats.create.return_value

    assert_basic_success(mock_genai_client, mock_chat, mock_ctx)

    assert mock_render_latex.call_count == expected_file_counts
    mock_render_latex.assert_has_calls([
        call("<tex>\\frac{1}{x}</tex>"), # Use call from unittest.mock
        call("<tex>-\\frac{1}{x^2}</tex>"),
    ])

    mock_send_long_messages.assert_called_once()

    args, kwargs = mock_send_long_messages.call_args
    sent_message_parts = args[1]

    expected_text_parts = [
        "The derivative of ",
        " is ",
    ]
    file_count = 0
    text_part_index = 0

    for part in sent_message_parts:
        if isinstance(part, str):
            # Adjust assertion slightly if needed, checking containment might be safer
            assert expected_text_parts[text_part_index] in part
            text_part_index += 1
        elif isinstance(part, discord.File):
            assert part.filename in mock_filenames
            file_count += 1
        else:
             pytest.fail(f"Unexpected part type in sent message: {type(part)}")


    assert file_count == expected_file_counts
    assert text_part_index == len(expected_text_parts)

    mock_send_long_message_prompt_utils.assert_not_called()
    mock_send_image.assert_not_called()
    assert mock_os_remove.call_count == expected_file_counts
    mock_os_remove.assert_has_calls([
        call("mocked_latex_image1.png"),
        call("mocked_latex_image2.png"),
    ], any_order=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "Here's the LaTeX you requested: <tex>\\frac{1}{</tex>"},
    ],
    indirect=["mock_genai_client"],
)
@pytest.mark.parametrize( # Parametrize the fixture
    "mock_common_dependencies",
    [
        {
            "render_latex_config": {"return_value": None},
            "split_tex_config": {
                "return_value": ([
                    "Here's the LaTeX you requested: ",
                    "<tex>\\frac{1}{</tex>",
                ], True),
            },
            "check_tex_config": {
                "side_effect": lambda x: x.startswith("<tex>") and x.endswith("</tex>"),
            },
        },
    ],
    indirect=True,
)
async def test_prompt_invalid_latex(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict, # Inject the configured dependencies
)  -> None:
    """Tests the scenario with invalid LaTeX in the prompt."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_render_latex = mock_common_dependencies["render_latex"]
    mock_os_remove = mock_common_dependencies["os_remove"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_error_msg = r"<tex>\frac{1}{</tex> (Contains Invalid LaTeX Expressions)"
    expected_number_of_sent_prompts = 2

    mock_chat = mock_genai_client.aio.chats.create.return_value

    assert_basic_success(mock_genai_client, mock_chat, mock_ctx)

    mock_render_latex.assert_called_once_with("<tex>\\frac{1}{</tex>")

    mock_send_long_messages.assert_called_once()
    args, _ = mock_send_long_messages.call_args
    sent_prompts = args[1]

    assert len(sent_prompts) == expected_number_of_sent_prompts
    assert sent_prompts[0] == "Here's the LaTeX you requested: "
    assert sent_prompts[1] == expected_error_msg

    mock_send_long_message_prompt_utils.assert_not_called()
    mock_send_image.assert_not_called()
    mock_os_remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "response_text": "Valid: <tex>\\frac{1}{x}</tex>, "
                             "Invalid: <tex>\\frac{1}{</tex>",
        },
    ],
    indirect=["mock_genai_client"],
)
@pytest.mark.parametrize(
    "mock_common_dependencies",
    [
        {
            "render_latex_config": {
                "side_effect": ["mocked_latex_image.png", None],
            },
            "split_tex_config": {
                "return_value":
                    (
                        [
                            "Valid: ",
                            "<tex>\\frac{1}{x}</tex>",
                            ", Invalid: ",
                            "<tex>\\frac{1}{</tex>",
                        ],
                        True,
                    ),
                 },
            "check_tex_config": {
                "side_effect":
                     lambda x: x.startswith("<tex>") and x.endswith("</tex>"),
            },
        },
    ],
    indirect=True,
)
async def test_prompt_mixed_valid_and_invalid_latex(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests scenarios with both valid and invalid LaTeX in the same response."""
    mock_valid_filename = "mocked_latex_image.png"

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_render_latex = mock_common_dependencies["render_latex"]
    mock_os_remove = mock_common_dependencies["os_remove"]

    mock_chat = mock_genai_client.aio.chats.create.return_value

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_render_latex_count = 2

    assert_basic_success(mock_genai_client, mock_chat, mock_ctx)

    assert mock_render_latex.call_count == expected_render_latex_count
    mock_render_latex.assert_has_calls([
        unittest.mock.call("<tex>\\frac{1}{x}</tex>"),
        unittest.mock.call("<tex>\\frac{1}{</tex>"),
    ])

    mock_send_long_messages.assert_called_once()
    args, _ = mock_send_long_messages.call_args
    sent_message_parts = args[1]

    expected_text_parts = [
        "Valid: ",
        ", Invalid: ",
        r"<tex>\frac{1}{</tex> (Contains Invalid LaTeX Expressions)",
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

    mock_send_long_message_prompt_utils.assert_not_called()
    mock_send_image.assert_not_called()
    mock_os_remove.assert_called_once_with(mock_valid_filename)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> {clear}", "is_admin": True},
    ],
    indirect=["mock_ctx"],
)
async def test_clear_admin(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict, # Request the fixture
) -> None:
    """Tests the clear success scenario of the prompt command."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_memory_clear = mock_common_dependencies["clear_memory"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_success_message = ("Alright, I have cleared my context. "
                                "What are we gonna talk about?")

    mock_chat = mock_genai_client.aio.chats.create.return_value

    assert_not_needed(
        mock_genai_client,
        mock_chat,
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )

    mock_memory_clear.assert_called_once()
    mock_ctx.reply.assert_called_once_with(expected_success_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> {clear}", "is_admin": False},
    ],
    indirect=["mock_ctx"],
)
async def test_clear_no_admin(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests the fail clear scenario of the prompt command without admin."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_memory_clear = mock_common_dependencies["clear_memory"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_warning_msg = "You don't have the necessary permissions for this!"

    mock_chat = mock_genai_client.aio.chats.create.return_value

    assert_not_needed(
        mock_genai_client,
        mock_chat,
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
    )

    mock_memory_clear.assert_not_called()
    mock_ctx.reply.assert_called_once_with(expected_warning_msg, ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize( # Parametrize the fixture
    "mock_common_dependencies",
    [
        { # Provide specific configurations
            "load_memory_config": {"return_value": "This is a test memory string."},
        },
    ],
    indirect=True,
)
async def test_memory_load_empty(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict, # Inject the configured dependencies
) -> None:
    """Test memory loading behavior when the memory list is initially empty."""
    mock_load_memory = mock_common_dependencies["load_memory"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_load_memory.assert_called_once()
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]

    assert sent_prompt[0].startswith("This is the memory you saved:")
    assert "This is a test memory string." in sent_prompt[0]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_common_dependencies",
    [
        {
            "get_memory_config": {"return_value": ["some", "existing", "memory"]},
        },
    ],
    indirect=True,
)
async def test_memory_load_not_empty(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Test that load_memory is NOT called when the memory list is NOT empty."""
    mock_load_memory = mock_common_dependencies["load_memory"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_load_memory.assert_not_called()
    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert "history" in kwargs
    assert kwargs["history"] == ["some", "existing", "memory"]

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
                ),
            ],
            "response_text": "",
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_single_safety_blocked(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Test a single blocked safety rating."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    assert_safety_blocked(
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
        expected_reason_text="Harassment",
    )


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
            "response_text": "",
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_multiple_safety_blocked(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Test multiple blocked safety ratings."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    assert_safety_blocked(
        mock_ctx,
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
        expected_reason_text="Harassment, Hate Speech",
    )

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_file",
    [
        {
            "file_path": Path("temp") / "uploaded_test_image.png",
            "uri": "mock_uri",
            "mime_type": "image/png",
        },
    ],
    indirect=["mock_file"],
)
async def test_single_attachment_success(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_file: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests a single attachment, successful upload."""
    attachment_data = [
        {
            "filename": Path(mock_file.name).name.replace("uploaded_",""),
            "content_type": mock_file.mime_type,
        },
    ]
    mock_attachments, _ = create_mock_attachments(attachment_data)
    mock_ctx.message.attachments = mock_attachments
    mock_attachment = mock_attachments[0]

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_handle_attachment = mock_common_dependencies["handle_attachment"]
    mock_wait_for_file_active = mock_common_dependencies["wait_for_file_active"]
    mock_os_remove = mock_common_dependencies["os_remove"]

    mock_handle_attachment.return_value = ([mock_file.name], [mock_file])

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_amount_of_sent_prompts = 3

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_handle_attachment.assert_called_once_with(mock_attachment, mock_genai_client)
    mock_wait_for_file_active.assert_called_once_with(mock_file)

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert len(sent_prompt) == expected_amount_of_sent_prompts
    assert isinstance(sent_prompt[2], Part)
    assert hasattr(sent_prompt[2], "file_data")
    assert sent_prompt[2].file_data.file_uri == "mock_uri"
    assert sent_prompt[2].file_data.mime_type == "image/png"

    mock_os_remove.assert_called_once_with(mock_file.name)

    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        DEFAULT_MOCK_RESPONSE_TEXT,
        DEFAULT_CHAR_LIMIT,
    )
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_attachments_success(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests multiple attachments, all successful."""
    attachment_data = [
        {"filename": "image1.png", "content_type": "image/png"},
        {"filename": "document.pdf", "content_type": "application/pdf"},
    ]
    mock_attachments, mock_files = create_mock_attachments(attachment_data)
    mock_ctx.message.attachments = mock_attachments

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_handle_attachment = mock_common_dependencies["handle_attachment"]
    mock_wait_for_file_active = mock_common_dependencies["wait_for_file_active"]
    mock_os_remove = mock_common_dependencies["os_remove"]
    mock_handle_attachment.side_effect = [([mf.name], [mf]) for mf in mock_files]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_amount_of_sent_prompts = 4 # Timestamp, text, file1, file2

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_handle_attachment.assert_has_calls([
        unittest.mock.call(mock_attachments[0], mock_genai_client),
        unittest.mock.call(mock_attachments[1], mock_genai_client),
    ])
    assert mock_handle_attachment.call_count == len(mock_attachments)

    # Assert wait_for_file_active was called for each genai.File
    mock_wait_for_file_active.assert_has_calls([
        unittest.mock.call(mock_files[0]),
        unittest.mock.call(mock_files[1]),
    ])
    assert mock_wait_for_file_active.call_count == len(mock_files)

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    # Verify prompt structure and file data parts
    assert len(sent_prompt) == expected_amount_of_sent_prompts
    assert sent_prompt[1] == "Hello, world!"
    assert sent_prompt[2].file_data.file_uri == "mock_uri_image1.png"
    assert sent_prompt[2].file_data.mime_type == "image/png"
    assert sent_prompt[3].file_data.file_uri == "mock_uri_document.pdf"
    assert sent_prompt[3].file_data.mime_type == "application/pdf"

    # Assert os.remove was called for each file path
    mock_os_remove.assert_has_calls(
        [
            unittest.mock.call(mock_files[0].name),
            unittest.mock.call(mock_files[1].name),
        ],
        any_order=True,
    )
    assert mock_os_remove.call_count == len(mock_files)

    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        DEFAULT_MOCK_RESPONSE_TEXT,
        DEFAULT_CHAR_LIMIT,
    )
    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


# ? Rework this as the logic is no longer correct
@pytest.mark.asyncio
async def test_attachment_failure(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Tests a single attachment, but handle_attachment fails."""
    mock_attachment = AsyncMock(spec=discord.Attachment)
    mock_attachment.filename = "failed_image.png"
    mock_attachment.content_type = "image/png"
    mock_ctx.message.attachments = [mock_attachment]

    error_message = "Yes"

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_handle_attachment = mock_common_dependencies["handle_attachment"]
    mock_wait_for_file_active = mock_common_dependencies["wait_for_file_active"]
    mock_os_remove = mock_common_dependencies["os_remove"]

    mock_handle_attachment.return_value = Exception(error_message)

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_amount_of_prompts = 2
    expected_error_message = (f"Error: Failed to upload attachment(s). "
                              f"Continuing as if the files are not uploaded. "
                              f"Error: `{error_message}`.")

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()

    mock_handle_attachment.assert_called_once_with(mock_attachment, mock_genai_client)
    mock_wait_for_file_active.assert_not_called()

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert sent_prompt[1] == "Hello, world!"
    assert len(sent_prompt) == expected_amount_of_prompts

    # Check that both the error message and the final response were sent
    mock_send_long_message_prompt_utils.assert_any_call(
        mock_ctx,
        expected_error_message,
        DEFAULT_CHAR_LIMIT,
    )
    mock_send_long_message_prompt_utils.assert_any_call(
        mock_ctx,
        DEFAULT_MOCK_RESPONSE_TEXT,
        DEFAULT_CHAR_LIMIT,
    )
    # Ensure it was called exactly twice (once for error, once for response)
    assert mock_send_long_message_prompt_utils.call_count == expected_amount_of_prompts

    mock_os_remove.assert_not_called() # File path wasn't returned on failure

    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "executable_code": "print('Hello, World!')",
            "code_execution_result": "Hello, World!",
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_handle_executable_code_and_code_execution_result(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test the handling of executable code and code execution result with no images."""
    tool = Tool(code_execution=ToolCodeExecution())

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]

    command_func = prompt([tool], mock_genai_client)
    await command_func(mock_ctx)

    expected_executable_code = "Code:\n```python\nprint('Hello, World!')\n```"
    expected_code_exec_result = "Output:\n```\nHello, World!\n```"

    mock_send_long_message_prompt_utils.assert_has_calls([
        call(
            mock_ctx,
            DEFAULT_MOCK_RESPONSE_TEXT,
            DEFAULT_CHAR_LIMIT,
        ),
        call(mock_ctx, expected_executable_code, DEFAULT_CHAR_LIMIT),
        call(mock_ctx, expected_code_exec_result, DEFAULT_CHAR_LIMIT),
    ])

    _, kwargs = mock_genai_client.aio.chats.create.call_args
    assert_tools(kwargs, tool)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {
            "executable_code": "print('Some Matplotlib Magic!')",
            "inline_data": "random image byte data hehe",
        },
    ],
    indirect=["mock_genai_client"],
)
async def test_handle_executable_code_and_send_image(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests handling of executable code producing inline image data using anyio."""
    tool = Tool(code_execution=ToolCodeExecution())

    # Get mocks from the updated fixture
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_os_remove = mock_common_dependencies["os_remove"]
    mock_anyio_open = mock_common_dependencies["mock_anyio_open"]
    mock_async_file_handle = mock_common_dependencies["mock_async_file_handle"]

    command_func = prompt([tool], mock_genai_client)
    await command_func(mock_ctx)

    expected_code = "Code:\n```python\nprint('Some Matplotlib Magic!')\n```"
    expected_text = DEFAULT_MOCK_RESPONSE_TEXT
    expected_amount_of_prompts = 2

    mock_send_long_message_prompt_utils.assert_has_calls([
        unittest.mock.call(
            mock_ctx,
            expected_text,
            DEFAULT_CHAR_LIMIT),
        unittest.mock.call(
            mock_ctx,
            expected_code,
            DEFAULT_CHAR_LIMIT),
    ], any_order=False)

    assert mock_send_long_message_prompt_utils.call_count == expected_amount_of_prompts

    mock_send_long_messages.assert_not_called()

    mock_send_image.assert_called_once()

    temp_filename_used_by_prompt = unittest.mock.ANY # Capture if needed
    # Assert anyio.open_file was called (via the patch)
    mock_anyio_open.assert_called_once_with(temp_filename_used_by_prompt, "wb")
    # Assert the async write method was called on the mock file handle
    mock_async_file_handle.write.assert_called_once_with(b"random image byte data hehe")

    # os.remove is likely still synchronous after the async context block
    mock_os_remove.assert_called_once_with(temp_filename_used_by_prompt)

    _, kwargs = mock_genai_client.aio.chats.create.call_args
    assert_tools(kwargs, tool)

# <<<--- Rest of existing tests (grounding, youtube, errors, etc.) --->>>
# These tests don't directly interact with the file opening mock,
# so they should remain unchanged unless they have other dependencies
# on the exact implementation details modified by the anyio change.

@pytest.mark.parametrize("mock_genai_client", [
    {
        "response_text": DEFAULT_MOCK_RESPONSE_TEXT,
        "grounding_details": [
            {"title": "Source 1", "uri": "https://source1.com"},
            {"title": "Source 2 (Blog)", "uri": "https://blog.source2.com/article"},
        ],
    },
], indirect=True)
@pytest.mark.parametrize( # Parametrize the common dependencies fixture
    "mock_common_dependencies",
    [
        {
            "create_grounding_markdown_config": {
                "return_value": (
                        "## Grounding Sources:\n\n"
                        "- [Source 1](https://source1.com)\n"
                        "- [Source 2 (Blog)](https://blog.source2.com/article)"
                ),
            },
        },
    ],
    indirect=True, # Target the fixture
)
@pytest.mark.asyncio
async def test_grounding_markdown(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) ->  None:
    """Test grounding markdown generation."""
    tool = Tool(google_search=GoogleSearch())
    expected_source_markdown = ("## Grounding Sources:\n\n"
                                "- [Source 1](https://source1.com)\n"
                                "- [Source 2 (Blog)](https://blog.source2.com/article)")

    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_grounding = mock_common_dependencies["create_grounding_markdown"]

    command_func = prompt([tool], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_response = mock_chat.send_message.return_value
    assert mock_response is not None, (
        "mock_chat.send_message should have returned a response object"
    )
    assert hasattr(mock_response, "candidates"), (
        "Response object should have candidates"
    )
    assert len(mock_response.candidates) > 0, (
        "Response should have at least one candidate"
    )
    mock_candidate = mock_response.candidates[0]

    mock_grounding.assert_called_once_with(mock_candidate)

    expected_final_message = f"{DEFAULT_MOCK_RESPONSE_TEXT}\n{expected_source_markdown}"
    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        expected_final_message,
        DEFAULT_CHAR_LIMIT,
    )

    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()

    args, kwargs = mock_genai_client.aio.chats.create.call_args
    assert "config" in kwargs
    assert kwargs["config"].tools == [tool]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",
    [
        {"message_content": "<@12345> A youtube link! https://www.youtube.com/watch?v=t5XOXQqsTvM"},
    ],
    indirect=["mock_ctx"],
)
async def test_youtube_processing(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    datetime_mock: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test the YouTube processing function."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]

    assert sent_prompt[0] == ("Monday, January 01, 2024 12:00:00 UTC, "
                              "TestUser With Display Name TestUserDisplayName "
                              "and ID 67890: ")
    assert sent_prompt[1] == "A youtube link! "
    assert sent_prompt[2] == Part(file_data=FileData(file_uri="https://www.youtube.com/watch?v=t5XOXQqsTvM"))


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
async def test_malformed_function_call(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test multiple blocked safety ratings."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_err_msg = "Seems like my function calling tool is malformed. Try again!"

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()
    mock_ctx.typing.assert_called_once()
    mock_ctx.reply.assert_called_once_with(expected_err_msg)
    mock_send_long_message_prompt_utils.assert_not_called()
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
async def test_thought(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test the thought handling system."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_save_temp_config = mock_common_dependencies["save_temp_config"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_response = "\nSo, I thought.\n(This reply have a thought)"

    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        expected_response,
        DEFAULT_CHAR_LIMIT,
    )
    mock_save_temp_config.assert_called_once_with(
        thought=["<thought>Big Thinking 🤔</thought>"],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_genai_client",
    [
        {"response_text": "<store>Big Secret TeeHee</store>\nYou'll never know!"},
    ],
    indirect=["mock_genai_client"],
)
@pytest.mark.asyncio
async def test_secret(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Tests secret handling."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_save_temp_config = mock_common_dependencies["save_temp_config"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        "\nYou'll never know!",
        DEFAULT_CHAR_LIMIT,
    )
    mock_save_temp_config.assert_called_once_with(
        secret=["<store>Big Secret TeeHee</store>"],
    )

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_temp_config",
    [
        {
            "uwu": True,
            "model": DEFAULT_MODEL,
            "system_prompt": "You are a helpful assistant.",
        },
    ],
    indirect=["mock_temp_config"],
)
@pytest.mark.parametrize(
    "mock_common_dependencies",
    [
        {
            "uwuify_config": {"return_value": f"{DEFAULT_MOCK_RESPONSE_TEXT} :3"},
        },
    ],
    indirect=True,
)
async def test_uwu(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_temp_config: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests uwuification when enabled."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_uwuify_sentence = mock_common_dependencies["uwuify"]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    original_response = DEFAULT_MOCK_RESPONSE_TEXT
    mock_uwuify_sentence.assert_called_once_with(original_response)
    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        f"{DEFAULT_MOCK_RESPONSE_TEXT} :3",
        DEFAULT_CHAR_LIMIT,
    )
    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_genai_client.aio.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once()


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
async def test_finish_reason_max_tokens(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test handling when Gemini finishes because of max tokens."""
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_warning_reply = f"{DEFAULT_MOCK_RESPONSE_TEXT}\n(Response May Be Cut Off)"

    mock_send_long_message_prompt_utils.assert_called_once_with(
        mock_ctx,
        expected_warning_reply,
        DEFAULT_CHAR_LIMIT,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_ctx",  # Standard context is likely fine
    [{"message_content": "<@12345> Hello, world!"}],
    indirect=["mock_ctx"],
)
@pytest.mark.parametrize(  # Parametrize common deps to control get_memory
    "mock_common_dependencies",
    [{"get_memory_config": {"return_value": ["some interesting memories"]}}],
    indirect=True,
)
async def test_prompt_with_memory(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_temp_config: dict,
    mock_common_dependencies: dict,
) -> None:
    """Tests the memory scenario of the prompt command with mocked datetime."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_chat = mock_genai_client.aio.chats.create.return_value # Get after call
    mock_send_long_message_prompt_utils = mock_common_dependencies[
        "send_long_message_prompt_utils"
    ]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]
    mock_load_memory = mock_common_dependencies["load_memory"]

    # Core API interaction checks
    assert_basic_success(mock_genai_client, mock_chat, mock_ctx)

    # Check arguments used for API call, including history
    expected_config = generate_config_normal(HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
    assert_chats_create_args(
        mock_genai_client,
        expected_config=expected_config,
        expected_model=mock_temp_config["model"],
        expected_history=["some interesting memories"], # Pass the expected memory
    )

    # Check the final output message
    assert_sent_simple_response(
        mock_send_long_message_prompt_utils,
        mock_send_long_messages,
        mock_send_image,
        mock_ctx,
        DEFAULT_MOCK_RESPONSE_TEXT, # Assuming default response text
    )

    # Verify memory load wasn't called (as memory was already present)
    mock_load_memory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_temp_config",
    [
        {"model": "gemini-2.0-flash-exp-image-generation"},
    ],
    indirect=["mock_temp_config"],
)
async def test_model_with_image_gen(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_temp_config: dict,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test a model with image generation capabilities."""
    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)
    expected_config = generate_config_image(HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)

    mock_chat = mock_genai_client.aio.chats.create.return_value

    mock_genai_client.aio.chats.create.assert_called_once_with(
        model="gemini-2.0-flash-exp-image-generation",
        config=expected_config,
    )

    chat_args, chat_kwargs = mock_chat.send_message.call_args
    sent_prompt = chat_args[0]
    assert sent_prompt == "Hello, world!"

@pytest.mark.asyncio
async def test_client_error_handling(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: dict,
) -> None:
    """Tests ClientError handling using common dependencies fixture."""
    send_long_message = mock_common_dependencies["send_long_message"]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    response = Response()
    response.status_code = 400
    response._content = (b'{"error": {"code": 400, "message": "Invalid input", '
                         b'"status": "INVALID_ARGUMENT"}}')
    mock_genai_client.aio.chats.create.side_effect = errors.ClientError(
        code=400, response=response,
    )

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    mock_genai_client.aio.chats.create.assert_called_once()

    expected_error_block = ("400 INVALID_ARGUMENT. "
                            "{'error': {'code': 400, 'message': 'Invalid input', "
                            "'status': 'INVALID_ARGUMENT'}}")
    expected_error_msg = (
        "Something went wrong on our side. "
        "Please submit a bug report at the GitHub repo for this bot, "
        "or ping the creator.\n"
        f"```{expected_error_block}```"
    )

    send_long_message.assert_called_once_with(
        mock_ctx,
        expected_error_msg,
        DEFAULT_CHAR_LIMIT,
    )

    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()

    mock_ctx.typing.assert_called_once()

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_chat.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_server_error_handling(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test ServerError handling."""
    send_long_message = mock_common_dependencies["send_long_message"]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    response = Response()
    response.status_code = 500
    response._content = (b'{"error": {"code": 500, "message": "Internal Server Error", '
                         b'"status": "INTERNAL_SERVER_ERROR"}}')

    mock_genai_client.aio.chats.create.side_effect = errors.ServerError(
        code=500, response=response,
    )

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    send_long_message.assert_called_once_with(
        mock_ctx,
        (
            "Something went wrong on Google's end / Gemini. "
            "Please wait for a while and try again.\n"
            "```500 INTERNAL_SERVER_ERROR. "
            "{'error': {'code': 500, 'message': 'Internal Server Error', 'status': 'INTERNAL_SERVER_ERROR'}}```"  # noqa: E501
        ),
        DEFAULT_CHAR_LIMIT,
    )

    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()

    mock_ctx.typing.assert_called_once()

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_chat.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_exception_error_handling(
    mock_ctx: AsyncMock,
    mock_genai_client: MagicMock,
    mock_common_dependencies: MagicMock,
) -> None:
    """Test an Exception."""
    send_long_message = mock_common_dependencies["send_long_message"]
    mock_send_long_messages = mock_common_dependencies["send_long_messages"]
    mock_send_image = mock_common_dependencies["send_image"]

    mock_genai_client.aio.chats.create.side_effect = Exception("An exception.")

    command_func = prompt([], mock_genai_client)
    await command_func(mock_ctx)

    expected_error_message = (
        "Something went wrong. "
        "Please review the error and maybe submit a bug report.\n"
        "```An exception.```"
    )

    send_long_message.assert_called_once_with(
        mock_ctx,
        expected_error_message,
        DEFAULT_CHAR_LIMIT,
    )

    mock_send_long_messages.assert_not_called()
    mock_send_image.assert_not_called()

    mock_ctx.typing.assert_called_once()

    mock_chat = mock_genai_client.aio.chats.create.return_value
    mock_chat.send_message.assert_not_called()


def test_youtube_regex() -> None:
    """Test a regex pattern."""
    def verify(url: str) -> bool:
        """Verify a regex pattern.

        Args:
            url: the link of the file

        Returns: A bool to check if

        """
        return bool(regex.search(YOUTUBE_PATTERN, url))

    assert verify("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert verify("youtube.com/watch?v=dQw4w9WgXcQ")
    assert verify("https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert verify("http://youtube.com/watch?v=dQw4w9WgXcQ")

    assert not verify("https://www.youtube.com/watc?v=dQw4w9WgXcQ")
    assert not verify("https://www.youtube.com/watch?=dQw4w9WgXcQ")
    assert not verify("https://www.youtube.com/watch?vdQw4w9WgXcQ")
    assert not verify("https:www.youtube.com/watch?vdQw4w9WgXcQ")
    assert not verify("https://www.youtube.com/?v=dQw4w9WgXcQ")
    assert not verify("https://www.youtube.com/dQw4w9WgXcQ")
    assert not verify("https://www.youtube.comwatch?v=dQw4w9WgXcQ")
    assert not verify("https//www.youtube.com/watch?vdQw4w9WgXcQ")

    assert not verify("https://www.youtube.com/feed/history")
    assert not verify("https://www.youtube.com/feed")
    assert not verify("https://www.youtube.com/feed/trending?bp=6gQJRkVleHBsb3Jl")
    assert not verify("https://www.youtube.com/channel/UCYfdidRxbB8Qhf0Nx7ioOYw")
    assert not verify("https://studio.youtube.com/")
    assert not verify("https://youtube.com")
    assert not verify("https://www.youtube.com/@alanbecker")
    assert not verify("https://www.youtube.com/account")

    assert not verify("https://python.org/")
    assert not verify("https://python.org")
    assert not verify("https://aistudio.google.com/app/prompts/new_chat")

    # fails with a single slash↓
    # assert not verify('https:/www.youtube.com/watch?v=dQw4w9WgXcQ')
    # Doesn't work with YouTube short
    # assert verify('https://www.youtube.com/shorts/xIMlJUwB1m8')
