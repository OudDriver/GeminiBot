import unittest
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import pytest
import wikipedia

from packages.tools.internet import (
    get_webpage_content_ddg,
    get_wikipedia_page,
    make_get_request,
    search_duckduckgo,
)


@pytest.fixture(autouse=True)
def mock_load_config() -> Generator[None, None, None]:
    """Mock save_temp_config."""
    with patch("packages.internet.save_temp_config") as mock:
        mock.return_value = None
        yield


@pytest.fixture
def mock_ddgs() -> Generator[MagicMock, None, None]:
    """Mock DuckDuckDoSearch."""
    with patch("packages.internet.DDGS") as mock_ddgs_class:
        mock_ddgs_instance = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance
        yield mock_ddgs_instance



@pytest.fixture
def mock_requests_get() -> Generator[MagicMock, None, None]:
    """Mock requests.get."""
    with patch("packages.internet.requests.get") as mock_get:
        yield mock_get



@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Mock the httpx client."""
    with patch("packages.internet.httpx.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client_instance
        yield mock_client_instance



@pytest.fixture
def mock_wikipedia_page() -> Generator[MagicMock, None, None]:
    """Mock wikipedia.page."""
    with patch("packages.internet.wikipedia.page") as mock_page:
        yield mock_page


def test_search_duckduckgo_basic(mock_ddgs: MagicMock) -> None:
    """Test the basic success scenario for duckduckgo_search."""
    total_results = 2

    mock_results = [
        {"href": "https://example.com/1", "title": "Result 1", "body": ""},
        {"href": "https://example.com/2", "title": "Result 2", "body": ""},
    ]
    mock_ddgs.text.return_value = mock_results

    results = search_duckduckgo(
        "test query",
        max_results=total_results,
        get_website_content=False,
    )
    assert len(results) == total_results
    assert results[0]["href"] == "https://example.com/1"
    assert results[1]["href"] == "https://example.com/2"
    mock_ddgs.text.assert_called_once_with("test query", max_results=total_results)


def test_search_duckduckgo_with_content(mock_ddgs: MagicMock) -> None:
    """Test the success scenario with getting website content enabled."""
    total_results = 2
    mock_results_with_body = [
        {"href": "https://example.com/1", "title": "Result 1"},
        {"href": "https://example.com/2", "title": "Result 2"},
    ]
    mock_ddgs.text.return_value = mock_results_with_body

    with patch(
        "packages.internet.get_webpage_content_ddg",
        side_effect=["Content 1", "Content 2"],
    ) as mock_get_content:
        results = search_duckduckgo(
            "test query",
            max_results=total_results,
            get_website_content=True,
        )
        assert len(results) == total_results
        assert results[0]["body"] == "Content 1"
        assert results[1]["body"] == "Content 2"
        mock_get_content.assert_has_calls([
            unittest.mock.call("https://example.com/1"),
            unittest.mock.call("https://example.com/2"),
        ])
        assert mock_get_content.call_count == total_results
        mock_ddgs.text.assert_called_once_with("test query", max_results=total_results)


def test_get_webpage_content_ddg_with_https(mock_requests_get: MagicMock) -> None:
    """Test the success scenario with getting website content enabled and https.

    Includes testing scripts, body, and HTTP header functions.
    """
    mock_response = MagicMock()
    mock_response.content = (
        b"<html>"
        b"<body>"
        b"<h1>Test Content</h1>"
        b"<p>This is a test.</p>"
        b"<script>let x = 1;</script>"
        b"</body>"
        b"</html>"
    )
    mock_requests_get.return_value = mock_response

    content = get_webpage_content_ddg("https://example.com")
    assert content == "Test Content\nThis is a test."
    mock_requests_get.assert_called_once_with(
        "https://example.com",
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
                          "Gecko/20100101 Firefox/120.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )


def test_get_webpage_content_ddg_without_https(mock_requests_get: MagicMock) -> None:
    """Test the success scenario with getting website content enabled and https.

    Includes testing scripts, body, and HTTP header functions.
    """
    mock_response = MagicMock()
    mock_response.content = b"<html><body><h1>Another Test</h1></body></html>"
    mock_requests_get.return_value = mock_response
    content = get_webpage_content_ddg("example.com")

    assert content == "Another Test"
    mock_requests_get.assert_called_once_with(
        "https://example.com",
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
                          "Gecko/20100101 Firefox/120.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )



def test_make_get_request_basic_success(mock_httpx_client: MagicMock) -> None:
    """Test the basic success scenario of make_get_request."""
    mock_response = MagicMock()
    mock_httpx_client.get.return_value = mock_response

    mock_response.text = "Test content"
    mock_response.raise_for_status.return_value = None
    result = make_get_request("https://example.com")
    assert result == "Test content"
    mock_httpx_client.get.assert_called_once_with(
        "https://example.com",
        params={},
        follow_redirects=True,
    )
    mock_response.raise_for_status.assert_called_once()


def test_make_get_request_httpx_error(mock_httpx_client: MagicMock) -> None:
    """Test the error success scenario of make_get_request."""
    mock_response = MagicMock()
    mock_httpx_client.get.return_value = mock_response

    mock_response.raise_for_status.side_effect = httpx.HTTPError("Test error")
    result = make_get_request("https://example.com")
    assert result == "Test error"
    mock_httpx_client.get.assert_called_with(
        "https://example.com",
        params={},
        follow_redirects=True,
    )



def test_get_wikipedia_page_basic_successful(mock_wikipedia_page: MagicMock) -> None:
    """Test the basic success scenario of get_wikipedia_page."""
    mock_page = MagicMock()
    mock_page.content = "Wikipedia page content"
    mock_page.title = "Test Page"
    mock_wikipedia_page.return_value = mock_page
    result = get_wikipedia_page("Test Query")
    assert result == "Wikipedia page content"
    mock_wikipedia_page.assert_called_once_with("Test Query")


def test_get_wikipedia_page_error(mock_wikipedia_page: MagicMock) -> None:
    """Test the PageError scenario of get_wikipedia_page."""
    mock_wikipedia_page.side_effect = wikipedia.exceptions.PageError("Page not found")
    result = get_wikipedia_page("Nonexistent Query")
    assert result == "Sorry, I couldn't find a Wikipedia page for 'Nonexistent Query'."
    mock_wikipedia_page.assert_called_with("Nonexistent Query")


def test_get_wikipedia_disambiguition_error(mock_wikipedia_page: MagicMock) -> None:
    """Test the DisambiguationError scenario of get_wikipedia_page."""
    mock_wikipedia_page.side_effect = wikipedia.exceptions.DisambiguationError(
        "Test",
        ["Option 1", "Option 2"],
    )
    result = get_wikipedia_page("Ambiguous Query")
    assert (
        result == "Your query is ambiguous. Please be more specific. "
                  "Did you mean any of these?\n['Option 1', 'Option 2']"
    )
    mock_wikipedia_page.assert_called_with("Ambiguous Query")


def test_get_wikipedia_other_error(mock_wikipedia_page: MagicMock) -> None:
    """Test the normal Exception scenario of get_wikipedia_page."""
    mock_wikipedia_page.side_effect = Exception("Some other error")
    result = get_wikipedia_page("Error Query")
    assert (
        result == "Sorry, I encountered an error while "
                  "fetching information from Wikipedia."
    )
    mock_wikipedia_page.assert_called_with("Error Query")
