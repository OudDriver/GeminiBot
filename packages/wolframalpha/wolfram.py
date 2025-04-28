from __future__ import annotations

import logging
from typing import Any
from xml.parsers.expat import ExpatError

import httpx
import nest_asyncio
import xmltodict

from packages.utilities.general_utils import ensure_list
from packages.wolframalpha.errors import (
    WolframAPIError,
    WolframParseError,
    WolframQueryError,
    WolframRateLimitError,
)

nest_asyncio.apply()
logger = logging.getLogger(__name__)

RATE_LIMIT_CODE = 429
INVALID_APPID_CODE = 501

class WolframAlphaAPI:
    """A Python object for interacting with the Wolfram Alpha API."""

    def __init__(
            self,
            app_id: str,
            base_url: str = "https://api.wolframalpha.com/v2/",
    ) -> None:
        """Initializes the object.

        Args:
            app_id: Your Wolfram Alpha App ID.
            base_url: The base URL for the Wolfram Alpha API.
        """
        self.app_id: str = app_id
        self.base_url: str = base_url

    async def _make_request(
            self,
            endpoint: str,
            input_query: str,
            extra_inputs: dict[str, str],
    ) -> httpx.Response:
        """Makes a request to the Wolfram Alpha API.

        Args:
            endpoint: The API endpoint to call (e.g., "query").
            input_query: The input string for the query.
            extra_inputs: Additional parameters to send with the request.

        Returns:
            The HTTP response from the API.

        Raises:
            WolframRateLimitError: If a 429 status code is received.
            WolframQueryError: If a non-200/429 status code is received.
            WolframAPIError: For general network or request errors.
        """
        async with httpx.AsyncClient() as client:
            params: dict[str, str] = {"appid": self.app_id, "input": input_query}
            params.update(extra_inputs)

            logger.info(
                f"Making WolframAlpha request to {endpoint} "
                f"with params: {params}",
            )

            try:
                response = await client.get(self.base_url + endpoint, params=params)
                if response.status_code == RATE_LIMIT_CODE:
                    logger.error(
                        f"Wolfram API rate limit exceeded (429). "
                        f"Response: {response.text}",
                    )
                    msg = "Wolfram API rate limit exceeded."
                    raise WolframRateLimitError(msg)
                if response.status_code == INVALID_APPID_CODE:
                     logger.error(
                         f"Wolfram API Error 501: Invalid appid. "
                         f"Response: {response.text}",
                     )
                     msg = "Wolfram API Error 501: Invalid appid."
                     raise WolframQueryError(msg)
                response.raise_for_status()
                logger.debug(f"WolframAlpha response status: {response.status_code}")
                return response
            except httpx.TimeoutException as e:
                logger.exception("Wolfram API request timed out.")
                msg = f"Request timed out: {e}"
                raise WolframAPIError(msg) from e
            except httpx.RequestError as e:
                logger.exception("An error occurred during Wolfram API request.")
                msg = f"HTTP request failed: {e}"
                raise WolframAPIError(msg) from e
            except httpx.HTTPStatusError as e:
                logger.exception(
                    f"Wolfram API HTTP error: "
                    f"{e.response.status_code} - {e.response.text}",
                )
                msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                raise WolframQueryError(msg) from e


    @staticmethod
    async def _parse_xml(xml_string: str) -> dict[str, Any]:
        """Parses the XML response from Wolfram Alpha.

        Args:
            xml_string: The XML string to parse.

        Returns:
            A dictionary representing the parsed XML data.

        Raises:
            WolframParseError: If the XML cannot be parsed.
        """
        try:
            parsed_data = xmltodict.parse(xml_string)
            logger.debug("Successfully parsed WolframAlpha XML response.")
            return parsed_data
        except ExpatError as e:
            logger.exception("Failed to parse Wolfram Alpha XML response.")
            logger.debug(f"Problematic XML string: {xml_string[:500]}...")
            msg = f"XML parsing failed: {e}"
            raise WolframParseError(msg) from e
        except Exception as e:
             logger.exception("An unexpected error occurred during XML parsing.")
             msg = f"Unexpected XML parsing error: {e}"
             raise WolframParseError(msg) from e

    # Goodbye Show Steps API, We'll miss you.
    # Where did it even go anyway?

    @staticmethod
    def _process_subpod(
            subpods: list[dict[str, Any]],
            pod_title: str,
    ) -> dict[str, str]:
        """Helper function to process subpods and populate output.

        Args:
            subpods: A list of subpod dictionaries.
            pod_title: The title of the pod.

        Returns:
            A dictionary containing the extracted data from subpods.
        """
        output: dict[str, Any] = {} # Use Any initially for list value
        for subpod in subpods:
            # Use .get() for safer access
            subpod_title = subpod.get("@title", "")
            plaintext = subpod.get("plaintext")

            if plaintext is None:
                logger.warning(
                    f"Subpod '{subpod_title}' in pod '{pod_title}' has no plaintext.",
                )
                continue

            # Ensure the key exists and is a list before appending
            if pod_title not in output:
                output[pod_title] = []
            elif not isinstance(output[pod_title], list):
                 logger.warning(
                     f"Overwriting non-list value for pod '{pod_title}' "
                     f"during subpod processing.",
                 )
                 output[pod_title] = []
            output[pod_title].append(plaintext)

        final_output: dict[str, str] = {}
        for key, value in output.items():
            if isinstance(value, list):
                # Join multiple plaintexts with a separator
                final_output[key] = " | ".join(value)
            else:
                final_output[key] = value # Keep step-by-step as is

        return final_output

    @staticmethod
    def _handle_initial_status(
            dirty_input: dict[str, Any],
    ) -> tuple[bool, dict[str, Any] | None]:
        """Checks initial status flags (@error, @success) and returns early if needed.

        Args:
            dirty_input: The raw query result dictionary.

        Returns:
            A tuple: (should_proceed: bool, early_return_value: dict | None).
            If should_proceed is False, return early_return_value.
        """
        if dirty_input.get("@error") == "true":
            logger.warning(
                f"Passing through error dictionary from query: {dirty_input}",
            )
            return False, dirty_input

        if dirty_input.get("@success") != "true":
            logger.warning(
                f"Wolfram API indicated query failure or missing success flag. "
                f"Raw result: {dirty_input}",
            )
            error_details = dirty_input.get("error")
            if error_details:
                logger.error(f"Wolfram API error details: {error_details}")
                return False, {
                    "success": False,
                    "error": True,
                    "message": f"API Error: {error_details}",
                }
            suggestions = dirty_input.get("didyoumean")
            if suggestions:
                return False, {
                    "success": False,
                    "error": False,
                    "didyoumean": suggestions,
                }
            return False, dirty_input

        return True, None

    def _process_single_pod(self, pod: dict[str, Any]) -> dict[str, str]:
        """Processes a single pod dictionary to extract plaintext data.

        Args:
            pod: The dictionary representing a single pod.

        Returns:
            A dictionary containing the extracted data for this pod.
        """
        output: dict[str, str] = {}
        pod_title = pod.get("@title") # Already validated before calling

        subpod_data = pod.get("subpod")
        if subpod_data is None:
            logger.warning(f"Pod '{pod_title}' has no subpods.")
            return output # Return empty dict for this pod

        subpods = ensure_list(subpod_data)
        valid_subpods = [
            sp for sp in subpods
            if isinstance(sp, dict) and sp.get("plaintext") is not None
        ]

        if not valid_subpods:
            logger.warning(
                f"Pod '{pod_title}' has subpods but none have plaintext.",
            )
            return output

        if len(valid_subpods) > 1:
            output.update(self._process_subpod(valid_subpods, pod_title))
        elif len(valid_subpods) == 1:
            single_subpod = valid_subpods[0]
            plaintext = single_subpod.get("plaintext")
            subpod_title = single_subpod.get("@title", "")

            if subpod_title and subpod_title != pod_title:
                key = f"{pod_title}: {subpod_title}"
            else:
                key = pod_title

            output[key] = plaintext

        return output

    def clean_up(self, dirty_input: dict[str, Any]) -> dict[str, Any]:
        """Cleans up the output from Wolfram Alpha API.

        Args:
            dirty_input: The raw output from Wolfram Alpha API (queryresult node).

        Returns:
            A cleaned-up dictionary containing the relevant information,
            or the original input if it indicates an error or lacks expected structure.
        """
        should_proceed, early_return = self._handle_initial_status(dirty_input)
        if not should_proceed:
            return early_return # Return error, suggestion, or original dict

        # If we reach here, success="true"
        output: dict[str, str] = {}
        pods = ensure_list(dirty_input.get("pod"))

        if not pods:
            logger.warning("No pods found in successful Wolfram API response.")
            return {"success": True, "warning": "No pods found in result."}

        for pod in pods:
            # Basic validation of pod structure
            if not isinstance(pod, dict) or "@title" not in pod:
                logger.warning(f"Skipping invalid pod structure: {pod}")
                continue

            # Process the single pod and update the main output
            pod_output = self._process_single_pod(pod)
            output.update(pod_output)

        if not output:
            logger.warning(
                "Processing completed, but no data extracted from pods/subpods.",
            )
            return {"success": True, "warning": "No data extracted from pods."}

        # Add success flag to the final processed output
        # It's good practice to indicate success explicitly if we processed pods
        final_result = {"success": True}
        final_result.update(output)
        return final_result

class WolframAlphaFullAPI(WolframAlphaAPI):
    """Class for interacting with the Wolfram Alpha Full API."""

    async def query(
            self,
            input_string: str,
            extra_input: dict[str, str] | None = None,
    ) -> dict[str, Any]: # Return Any to allow error dicts
        """Sends a query to the Wolfram Alpha Full API.

        Args:
            input_string: The input string for the query.
            extra_input: Additional parameters to send with the request.

        Returns:
            A dictionary representing the query result, or an error dictionary
            if the request or parsing fails.
        """
        if extra_input is None:
            extra_input = {}

        try:
            response = await self._make_request("query", input_string, extra_input)
            # Check content type before parsing
            content_type = response.headers.get("content-type", "").lower()
            if "xml" not in content_type:
                 logger.error(
                     f"Unexpected content type received: {content_type}. "
                     f"Body: {response.text[:500]}...",
                 )
                 msg = f"Expected XML content type, got {content_type}"
                 raise WolframParseError(msg)

            doc = await self._parse_xml(response.text)

            # Basic validation of parsed structure
            if not isinstance(doc, dict) or "queryresult" not in doc:
                 logger.error(
                     f"Parsed XML does not contain 'queryresult' root element. "
                     f"Parsed: {doc}",
                 )
                 msg = "Parsed XML missing 'queryresult' root."
                 raise WolframParseError(msg)

            return doc["queryresult"]

        except (WolframAPIError, WolframParseError) as e:
            logger.exception(
                "Failed to execute Wolfram Alpha query.",
            )
            error_result = {
                "@success": "false",
                "@error": "true",
                "message": f"Failed to query Wolfram Alpha: {e}",
            }
        except Exception as e:
             logger.exception("An unexpected error occurred in query method.")
             error_result = {
                "@success": "false",
                "@error": "true",
                "message": f"An unexpected error occurred: {e}",
            }

        # Ensure error_result is returned if an exception occurred
        # This structure handles the case where error_result
        # might be None if no exception happened,
        # although the logic above should always assign it in case of error.
        if error_result:
             return error_result
        logger.error(
            "Query method reached end without returning result or error dict.",
        )
        return {
            "@success": "false",
            "@error": "true",
            "message": "Unknown error occurred during query processing.",
        }

