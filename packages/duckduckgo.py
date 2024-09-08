import requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

def search_duckduckgo(query: str, max_results: int = 1, instant_answers: bool = True, regular_search_queries: bool = True, get_website_content: bool = True) -> list[dict]:
    """Searches DuckDuckGo for a given query and returns a list of results.

    Args:
        query: The search query. Required.
        max_results: The maximum number of results to return. Optional.
        instant_answers: Whether to include instant answers in the results. Either this or regular_search_queries must be True. Both can be True.
                         If an instant answer is found, only the instant answer is returned. Either this or instant_answers must be True. Both can be True.
        regular_search_queries: Whether to perform a regular search if no instant answer is found.
        get_website_content: Whether to fetch the content of each website in the search results.
                             Recommended for more details. Set this value to false if not needed.

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
    maxres = int(max_results)
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
            print(answer_dict)
            return [answer_dict]
        elif regular_search_queries:
            results = []
            for result in ddgs.text(query, region='wt-wt', safesearch='moderate', timelimit=None, max_results=maxres):
                if get_website_content:
                    result["body"] = get_webpage_content(result["href"])
                results.append(result)
            print(results)
            return results
        else:
            return "One of ('instant_answers', 'regular_search_queries') must be True"

def get_webpage_content(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.5"}
    if not url.startswith("https://"):
        try:
            response = requests.get(f"https://{url}", headers=headers)
        except:
            response = requests.get(url, headers=headers)
    else:
        response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, features="lxml")
    for script in soup(["script", "style"]):
        script.extract()

    strings = soup.stripped_strings
    return '\n'.join([s.strip() for s in strings])
