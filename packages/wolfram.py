import httpx
import xmltodict
import regex
from typing import Dict, Any, List
import json
import logging
import nest_asyncio
import asyncio

from packages.utils import save_temp_config

nest_asyncio.apply()

# TODO add error handling (it's nonexistent now)
class WolframAlphaAPI:
    """
    A Python object for interacting with the Wolfram Alpha API.

    Attributes:
        app_id: Your Wolfram Alpha App ID.
        url: The base URL for the Wolfram Alpha API.
    """
    
    def __init__(self, app_id: str):
        self.app_id: str = app_id
        self.url: str = "https://api.wolframalpha.com/v2/"
    
    async def _make_request(self, endpoint: str, input_query: str, **kwargs: Any) -> httpx.Response:
        """
        Makes a request to the Wolfram Alpha API.

        Args:
            endpoint: The API endpoint to call (e.g., "query").
            input_query: The input string for the query.
            kwargs: Additional parameters to send with the request.

        Returns:
            The HTTP response from the API.
        """
        async with httpx.AsyncClient() as client:
            params: Dict[str, str] = {"appid": self.app_id, "input": input_query}
            params.update(kwargs) 
            
            logging.info(params)
            
            response = await client.get(self.url + endpoint, params=params)
            
            return response
        
    @staticmethod
    async def _parse_xml(xml_string: str) -> Dict[str, Any]:
        """
        Parses the XML response from Wolfram Alpha.

        Args:
            xml_string: The XML string to parse.

        Returns:
            A dictionary representing the parsed XML data.
        """
        return xmltodict.parse(xml_string)
    
    async def _find_steps_input(self, input_string: str) -> dict | None:
        temp_response = await self._make_request("query", input_string)
        temp_doc = await self._parse_xml(temp_response.text)
        temp_doc = temp_doc['queryresult']
        
        states = []
        if isinstance(temp_doc['pod'], list):
            for pod in temp_doc["pod"]:
                if "states" in pod:
                    states.extend(pod["states"]["state"] if isinstance(pod["states"]["state"], list) else [pod["states"]["state"]])
        else:
            states = temp_doc['pod']['states']['state']
            if not isinstance(states, list):
                states = [states]
        
        for state in states:
            if state['@name'] == 'Step-by-step solution':
                return {"podstate": state['@input'], "format":"plaintext"}
            
        return None 

    @staticmethod
    def _process_subpod(subpods: List[Dict[str, Any]], pod_title: str) -> Dict[str, str]:
        """
        Helper function to process subpods and populate output.

        Args:
            subpods: A list of subpod dictionaries.
            pod_title: The title of the pod.

        Returns:
            A dictionary containing the extracted data from subpods.
        """
        output: Dict[str, str] = {}
        for subpod in subpods:
            if regex.search("steps", subpod['@title']):
                output[subpod['@title']] = subpod.get('plaintext', 'No plain text available') 
            else:
                output.setdefault(pod_title, []).append(subpod['plaintext'])
        
        return output
    
    def clean_up(self, dirty_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans up the output from Wolfram Alpha API.

        Args:
            dirty_input: The raw output from Wolfram Alpha API.

        Returns:
            A cleaned-up dictionary containing the relevant information.
        """
        if dirty_input['@success'] != "true":
            return dirty_input
        
        output: Dict[str, Any] = {}

        for pod in dirty_input['pod'] if isinstance(dirty_input['pod'], list) else [dirty_input['pod']]:
            subpod_data = pod['subpod']
            if isinstance(subpod_data, list):
                output.update(self._process_subpod(subpod_data, pod['@title']))
            elif subpod_data.get('plaintext'):
                output[pod['@title']] = subpod_data['plaintext']

        return output
    
class WolframAlphaFullAPI(WolframAlphaAPI):
    """
    Class for interacting with the Wolfram Alpha Full API.
    """

    async def query(self, input_string: str, show_steps: bool = False, **kwargs: Any) -> Dict[str, Any]:
        """
        Sends a query to the Wolfram Alpha Full API.

        Args:
            input_string: The input string for the query.
            show_steps: Whether to show steps.
            kwargs: Additional parameters to send with the request.

        Returns:
            A dictionary representing the query result.
        """
        configs = {}
        
        if show_steps:
            show_steps_input = await self._find_steps_input(input_string)
            configs.update(show_steps_input)
        
        response = await self._make_request("query", input_string, **configs, **kwargs)
        doc = await self._parse_xml(response.text)
        
        return doc['queryresult']


def wolfram_alpha(query: str):
    """
    Sends a query to the Wolfram Alpha API.
    
    Args:
        query: The input string for the query.
        
    Returns:
        A dictionary representing the query result.
    """
    client = WolframAlphaFullAPI(json.load(open("config.json"))['WolframAPI'])
    
    loop = asyncio.get_running_loop()
    output = loop.run_until_complete(client.query(query))

    cleaned = client.clean_up(output)
    logging.info(client.clean_up(output))
    save_temp_config(
        tool_use={
            "name": "Wolfram Alpha",
            "input": query,
            "output": cleaned,
        }
    )
    return cleaned