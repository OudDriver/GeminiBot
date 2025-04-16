import requests
import httpx
import wikipedia
import logging

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing import Any, Dict

from packages.utils import save_temp_config


def search_duckduckgo(query: str, max_results: int, get_website_content: bool) -> list[dict[str, str]]:
    """Searches DuckDuckGo for a given query and returns a list of results. All arguments are required.

    Args:
        query: The search query.
        max_results: The maximum number of results to return.
        get_website_content: Whether to fetch the content of each website in the search results. Recommended for more details.

    Returns:
        A list of dictionaries, where each dictionary represents a search result.
    """
    query = query.strip("\"'")
    with DDGS() as ddgs:
        results = []
        for result in ddgs.text(query, max_results=max_results):
            if get_website_content:
                result["body"] = get_webpage_content_ddg(result["href"])
            results.append(result)
        save_temp_config(
            tool_use={
                "name": "Search DuckDuckGo",
                "input": {"query": query, "max_results": max_results, "get_website_content": get_website_content},
                "output": results,
            }
        )
        return results

def get_webpage_content_ddg(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.5"}
    if not url.startswith("https://"):
        response = requests.get(f"https://{url}", headers=headers)
    else:
        response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, features="lxml")
    for script in soup(["script", "style"]):
        script.extract()

    strings = soup.stripped_strings
    return '\n'.join([s.strip() for s in strings])

def make_get_request(url: str, *kwargs: Any) -> str:
    """
    Gets the content of a website.
    
    Args:
        url: The URL of the website.
        kwargs: Additional parameters to send with the request.
    
    Returns:
        The content of the website. 
    """
    
    params: Dict[str, str] = {}
    params.update(kwargs) 
    
    try:
        with httpx.Client() as client:
            response = client.get(url, params=params, follow_redirects=True)
            response.raise_for_status()
            save_temp_config(
                tool_use={
                    "name": "Make Get Request",
                    "input": url,
                    "output": response.text,
                }
            )
            return response.text
    except httpx.HTTPError as exc:
        logging.error(f"HTTP error occurred: {exc}")
        save_temp_config(
            tool_use={
                "name": "Make Get Request (Error)",
                "input": url,
                "output": str(exc),
            }
        )
        return str(exc)

def get_wikipedia_page(query: str) -> str:
    """
    Retrieves the content of a Wikipedia page based on the given query. Use this if you need more details about something.

    Args:
        query: The search query for the Wikipedia article.

    Returns:
        The Wikipedia page content as a string, or an error message if the search fails.
    """
    try:
        page = wikipedia.page(query)
        logging.info(f"Retrieval about {page.title} successful.")
        save_temp_config(
            tool_use={
                "name": "Get Wikipedia",
                "input": query,
                "output": page.content,
            }
        )
        return page.content
    except wikipedia.exceptions.PageError:
        logging.error(f"No Wikipedia page found for '{query}'.")
        save_temp_config(
            tool_use={
                "name": "Get Wikipedia (Error)",
                "input": query,
                "output": f"Sorry, I couldn't find a Wikipedia page for '{query}'.",
            }
        )
        return f"Sorry, I couldn't find a Wikipedia page for '{query}'."
    except wikipedia.exceptions.DisambiguationError as e:
        logging.error(f"Disambiguation error occurred: {e}")
        save_temp_config(
            tool_use={
                "name": "Get Wikipedia (Error)",
                "input": query,
                "output": f"Your query is ambiguous. Please be more specific. Did you mean any of these?\n{e.options}",
            }
        )
        return f"Your query is ambiguous. Please be more specific. Did you mean any of these?\n{e.options}"
    except Exception as e:
        logging.error(f"An error occurred while fetching Wikipedia data: {e}")
        save_temp_config(
            tool_use={
                "name": "Get Wikipedia (Error)",
                "input": query,
                "output": "Sorry, I encountered an error while fetching information from Wikipedia.",
            }
        )
        return (
            "Sorry, I encountered an error while fetching information from Wikipedia."
        )
