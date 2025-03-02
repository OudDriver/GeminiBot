import requests
import httpx
import wikipedia
import json
import logging

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing import Any, Dict

with open('config.json') as f:
    config = json.loads(f.read())

def search_duckduckgo(query: str, max_results: int, get_website_content: bool) -> list[dict[str, str]] | str:
    """Searches DuckDuckGo for a given query and returns a list of results.

    Args:
        query: The search query.
        max_results: The maximum number of results to return.
        get_website_content: Whether to fetch the content of each website in the search results. Recommended for more details. Set this value to True if needed.

    Returns:
        A list of dictionaries, where each dictionary represents a search result. 
        The format of the dictionary depends on whether an instant answer was found or a regular search was performed.

        For instant answers, the dictionary contains the following keys:
            - title: The search query.
            - body: The text of the instant answer.
            - href: The URL of the source of the instant answer.

        For regular search results, the dictionary contains the following keys:
            - title: The title of the search result.
            - href: The URL of the search result.
            - body: The content of the website (if `get_website_content` is True), otherwise None.
    """
    instant_answers = True
    regular_search_queries = True
    max_result = int(max_results)
    query = query.strip("\"'")
    with DDGS() as ddgs:
        if instant_answers:
            answer_list = ddgs.answers(query)
        else:
            answer_list = None
        if answer_list:
            answer_dict = answer_list[0]
            answer_dict["title"] = query
            answer_dict["body"] = answer_dict["text"]
            answer_dict["href"] = answer_dict["url"]
            answer_dict.pop('icon', None)
            answer_dict.pop('topic', None)
            answer_dict.pop('text', None)
            answer_dict.pop('url', None)
            logging.info(answer_dict)
            return [answer_dict]
        elif regular_search_queries:
            results = []
            for result in ddgs.text(query, region='wt-wt', safesearch='moderate', timelimit=None, max_results=max_result):
                if get_website_content:
                    result["body"] = get_webpage_content_ddg(result["href"])
                results.append(result)
            logging.info(results)
            return results
        else:
            return "One of ('instant_answers', 'regular_search_queries') must be True"

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
            return response.text
    except httpx.HTTPError as exc:
        logging.error(f"HTTP error occurred: {exc}")

def get_wikipedia_page(query: str) -> str:
    """
    Retrieves the content of a Wikipedia page based on the given query.

    Args:
        query: The search query for the Wikipedia article.

    Returns:
        The Wikipedia page content as a string, or an error message if the search fails.
    """
    try:
        # Use Wikipedia API to get the page content
        page = wikipedia.page(query)
        logging.info(f"Retrieval about {page.title} successful.")
        return page.content
    except wikipedia.exceptions.PageError:
        return f"Sorry, I couldn't find a Wikipedia page for '{query}'."
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Your query is ambiguous. Please be more specific. Did you mean any of these?\n{e.options}"
    except Exception as e:
        logging.error(f"An error occurred while fetching Wikipedia data: {e}")
        return "Sorry, I encountered an error while fetching information from Wikipedia."
