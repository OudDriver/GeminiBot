import asyncio
import json
from typing import Any

from packages.utilities.file_utils import save_temp_config
from packages.wolframalpha.errors import WolframAPIError, WolframParseError
from packages.wolframalpha.wolfram import WolframAlphaFullAPI, logger


def wolfram_alpha(query: str) -> dict[str, Any]: # Return Any to allow error dicts
    """Sends a query to the Wolfram Alpha API.

    Args:
        query: The input string for the query.

    Returns:
        A dictionary representing the query result, or an error dictionary.
    """
    app_id = None
    with open("config.json") as f:
        loaded_file = json.load(f)
        app_id = loaded_file.get("WolframAPI")
        if not app_id:
             logger.error("WolframAPI key not found or is empty in config.json")
             return {
                 "success": False,
                 "error": True,
                 "message": "WolframAlpha App ID not configured.",
             }

    client = WolframAlphaFullAPI(app_id)

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # No running loop
            logger.info(
                "No running asyncio loop found, "
                "creating a new one for Wolfram Alpha query.",
            )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            output = loop.run_until_complete(client.query(query))
            loop.close()
        else:
             output = loop.run_until_complete(client.query(query))

        if isinstance(output, dict) and output.get("@error") == "true":
             logger.error(
                 f"Wolfram Alpha query failed: "
                 f"{output.get('message', 'No details provided.')}",
             )
             cleaned = output
        else:
             cleaned = client.clean_up(output)

        # Log the final result (could be success data or an error dict)
        logger.info(f"Final Wolfram Alpha result for query '{query}': {cleaned}")

        # Save result regardless of success/failure for logging/debugging
        save_temp_config(
            tool_call={
                "name": "Wolfram Alpha",
                "input": query,
                "output": cleaned, # Save the cleaned output or error dict
            },
        )
        return cleaned

    except (WolframAPIError, WolframParseError) as e:
         logger.exception("Wolfram Alpha client error during query execution.")
         error_result = {"success": False, "error": True, "message": str(e)}
         # Attempt to save error state
         save_temp_config(
             tool_call={
                 "name": "Wolfram Alpha",
                 "input": query,
                 "output": error_result,
             },
         )
         return error_result
    except Exception as e:
        logger.exception("An unexpected error occurred in wolfram_alpha function.")
        error_result = {
            "success": False,
            "error": True,
            "message": f"Unexpected error: {e}",
        }
        # Attempt to save error state
        save_temp_config(
            tool_call={
                "name": "Wolfram Alpha",
                "input": query,
                "output": error_result,
            },
        )
        return error_result
