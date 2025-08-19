import logging
from typing import Any

import duckduckgo_search.exceptions
import httpx
import requests
import wikipedia
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from packages.utilities.file_utils import save_temp_config

logger = logging.getLogger(__name__)

def search_duckduckgo(
        query: str,
        max_results: int,
        get_website_content: bool,
) -> str | list[Any]:
    """Search DuckDuckGo for a given query and returns a list of results.

    All arguments are required.

    Args:
        query: The search query.
        max_results: The maximum number of results to return.
        get_website_content: Whether to fetch the content of each website.
                             Recommended for more details.

    Returns:
        A list of dictionaries, where each dictionary represents a search result.

    """
    query = query.strip("\"'")
    with DDGS() as ddgs:
        try:
            results = []
            for result in ddgs.text(query, max_results=max_results):
                if get_website_content:
                    result["body"] = get_webpage_content_ddg(result["href"])
                results.append(result)
            save_temp_config(
                tool_call={
                    "name": "Search DuckDuckGo",
                    "input": {
                        "query": query,
                        "max_results": max_results,
                        "get_website_content": get_website_content,
                    },
                    "output": results,
                },
            )
            logger.info("Search Duckduckgo successful!")
            return results
        except duckduckgo_search.exceptions.RatelimitException:
            logger.exception("Rate limit reached.")
            return "Rate limit reached. Please try again later."
        except duckduckgo_search.exceptions.DuckDuckGoSearchException as e:
            logger.exception("A search exception happened!")
            return f"A search exception happened! {e}"
        except Exception as e:
            logger.exception("An exception happened!")
            return f"An exception happened! {e}"


def get_webpage_content_ddg(url: str) -> str:
    """Get webpage content.

    Ensures to only take the website content, nothing else.

    Args:
        url: The url of the website to get.

    Returns:
        The contents of the site.

    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
            "Gecko/20100101 Firefox/120.0"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
    }
    if not url.startswith("https://"):
        response = requests.get(f"https://{url}", headers=headers, timeout=10)
    else:
        response = requests.get(url, headers=headers, timeout=10)

    soup = BeautifulSoup(response.content, features="lxml")
    for script in soup(["script", "style"]):
        script.extract()

    strings = soup.stripped_strings
    return "\n".join([s.strip() for s in strings])

def make_get_request(url: str, *kwargs: dict[str: str]) -> str:
    """Get the content of a website.

    Args:
        url: The URL of the website.
        kwargs: Additional parameters to send with the request.

    Returns:
        The content of the website.

    """
    params: dict[str, str] = {}
    params.update(kwargs)

    try:
        with httpx.Client() as client:
            response = client.get(url, params=params, follow_redirects=True)
            response.raise_for_status()
            save_temp_config(
                tool_call={
                    "name": "Make Get Request",
                    "input": url,
                    "output": response.text,
                },
            )
            return response.text
    except httpx.HTTPError as e:
        logger.exception("An HTTP error occurred.")
        save_temp_config(
            tool_call={
                "name": "Make Get Request (Error)",
                "input": url,
                "output": str(e),
            },
        )
        return str(e)

def get_wikipedia_page(query: str) -> str:
    """Retrieve the content of a Wikipedia page based on the given query.

    Use this if you need more details about something.

    Args:
        query: The search query for the Wikipedia article.

    Returns:
        The Wikipedia page content as a string, or an error message if the search fails.

    """
    try:
        page = wikipedia.page(query)
        logger.info(f"Retrieval about {page.title} successful.")
        save_temp_config(
            tool_call={
                "name": "Get Wikipedia",
                "input": query,
                "output": page.content,
            },
        )
        return page.content
    except wikipedia.exceptions.PageError:
        logger.exception(f"No Wikipedia page found for '{query}'.")
        error_msg = "Sorry, I couldn't find a Wikipedia page for '{query}'."
        save_temp_config(
            tool_call={
                "name": "Get Wikipedia (Error)",
                "input": query,
                "output": error_msg,
            },
        )
        return f"Sorry, I couldn't find a Wikipedia page for '{query}'."
    except wikipedia.exceptions.DisambiguationError as e:
        logger.exception("Disambiguation error occurred")
        error_msg = (
            f"Your query is ambiguous. Please be more specific. "
            f"Did you mean any of these?\n{e.options}"
        )
        save_temp_config(
            tool_call={
                "name": "Get Wikipedia (Error)",
                "input": query,
                "output": error_msg,
            },
        )
        return error_msg
    except Exception:
        logger.exception("An error occurred while fetching Wikipedia data.")
        error_msg = (
            "Sorry, I encountered an error "
            "while fetching information from Wikipedia."
        )
        save_temp_config(
            tool_call={
                "name": "Get Wikipedia (Error)",
                "input": query,
                "output": error_msg,
            },
        )
        return error_msg
