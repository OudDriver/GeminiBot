import logging

import requests
import json
from bs4 import BeautifulSoup

from packages.utilities.file_utils import save_temp_config

logger = logging.getLogger(__name__)

def get_lyrics(title: str, artist: str = "") -> None | str:
    """Gets lyrics and description for a given title and artist.

    Args:
        title: The title of the song.
        artist: The artist of the song (optional).

    Returns:
        The description and lyrics of the song.
    """
    tool_inputs = {"title": title, "artist": artist}
    logger.info(f"Starting lyrics fetch for: {title} {artist}")

    try:
        with open("config.json") as f:
            loaded_file = json.load(f)
            key = loaded_file.get("GeniusKey")

        if not key:
            logger.error("GeniusKey key not found or is empty in config.json")
            save_temp_config(tool_call={
                "name": "get_lyrics (Config Error)",
                "input": tool_inputs,
                "output": "Missing GeniusKey"
            })
            return "Configuration Error: GeniusKey missing"

        headers = {"Authorization": f"Bearer {key}"}

        request_url = f"https://api.genius.com/search?q={title} {artist}"
        logger.info(f"Searching Genius API: {request_url}")

        response = requests.get(request_url, headers=headers).json()
        hits = response.get("response", {}).get("hits", [])

        if not hits:
            logger.info("No hits found for query.")
            save_temp_config(tool_call={
                "name": "get_lyrics",
                "input": tool_inputs,
                "output": "Song not found"
            })
            return "Song not found"

        first_result = hits[0].get("result", {})
        api_path = first_result.get("api_path")

        if not api_path:
            logger.warning("API Path not found in search result.")
            return "Song API path not found."

        request_url_song = f"https://api.genius.com{api_path}"
        logger.info(f"Fetching song metadata: {request_url_song}")

        response_song = requests.get(request_url_song, headers=headers).json()
        song_response = response_song.get("response", {}).get("song", {})

        song_path = song_response.get("path")
        if not song_path:
            return "Song URL path couldn't be found."

        description_dom = song_response.get("description", {}).get("dom", {})

        def parse_dom(node):
            """Recursive helper to extract text from Genius DOM."""
            if isinstance(node, str):
                return node
            if isinstance(node, dict):
                children = node.get("children", [])
                return "".join(parse_dom(child) for child in children)
            return ""

        description_text = parse_dom(description_dom).strip()

        request_url_page_lyrics = f"https://genius.com{song_path}"
        logger.info(f"Scraping lyrics page: {request_url_page_lyrics}")

        page = requests.get(request_url_page_lyrics)
        soup = BeautifulSoup(page.text, "html.parser")

        containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})

        if not containers:
            msg = "Could not find lyrics content on the page HTML"
            logger.warning(msg)
            save_temp_config(tool_call={
                "name": "get_lyrics (Scrape Error)",
                "input": tool_inputs,
                "output": msg
            })
            return msg

        lyrics_text = ""
        for container in containers:
            # A. Clean hidden tags
            for useless_tag in container.find_all(attrs={"data-exclude-from-selection": "true"}):
                useless_tag.decompose()

            # B. Fix newlines
            for br in container.find_all("br"):
                br.replace_with("\n")

            # C. Extract text
            lyrics_text += container.get_text() + "\n"

        # Combine Description and Lyrics
        final_output = ""
        if description_text:
            final_output += f"[Description]\n{description_text}\n\n"

        final_output += f"[Lyrics]\n{lyrics_text.strip()}"

        logger.info("Successfully retrieved lyrics.")

        # SUCCESS LOG
        save_temp_config(tool_call={
            "name": "get_lyrics",
            "input": tool_inputs,
            "output": final_output
        })

        return final_output

    except Exception:
        # Logs the full traceback automatically
        logger.exception(f"Critical error in get_lyrics for input: {title} {artist}")

        # CRASH LOG (Generic error message in output)
        save_temp_config(tool_call={
            "name": "get_lyrics (Exception)",
            "input": tool_inputs,
            "output": "An internal error occurred."
        })
        return "An error occurred while fetching the lyrics."