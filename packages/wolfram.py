import httpx
import xmltodict
import re
from typing import Dict, Any, List
import json
import logging
import nest_asyncio
import asyncio

nest_asyncio.apply()

class WolframAlphaAPI:
    """
    A Python object for interacting with the Wolfram Alpha API.

    Attributes:
        app_id: Your Wolfram Alpha App ID.
        url: The base URL for the Wolfram Alpha API.
    """
    
    def __init__(self, app_id: str):
        self.app_id: str = app_id
        self.url: str = "http://api.wolframalpha.com/v2/"
    
    async def _make_request(self, endpoint: str, input: str, **kwargs: Any) -> httpx.Response:
        """
        Makes a request to the Wolfram Alpha API.

        Args:
            endpoint: The API endpoint to call (e.g., "query").
            input: The input string for the query.
            kwargs: Additional parameters to send with the request.

        Returns:
            The HTTP response from the API.
        """
        async with httpx.AsyncClient() as client:
            params: Dict[str, str] = {"appid": self.app_id, "input": input}
            params.update(kwargs) 
            
            logging.info(params)
            
            response = await client.get(self.url + endpoint, params=params)
            
            return response
        
    async def _parse_xml(self, xml_string: str) -> Dict[str, Any]:
        """
        Parses the XML response from Wolfram Alpha.

        Args:
            xml_string: The XML string to parse.

        Returns:
            A dictionary representing the parsed XML data.
        """

        root = xmltodict.parse(xml_string)
        return root
    
    async def find_steps_input(self, input_string):
        temp_response = await self._make_request("query", input_string)
        temp_doc = await self._parse_xml(temp_response.content)
        temp_doc = temp_doc['queryresult']
        
        if isinstance(temp_doc['pod'], list):
            for pods in temp_doc["pod"]:
                states = pods["states"]
                for state in states["state"]:
                    if state['@name'] == 'Step-by-step solution':
                        return {"podstate": state['@input'], "format":"plaintext"}
        
        states = temp_doc['pod']['states']['state']
        if states['@name'] == 'Step-by-step solution':
            step_by_step_input = states['@input']   
            return {"podstate":step_by_step_input, "format":"plaintext"}
    
    def process_subpod(self, subpods: List[Dict[str, Any]], pod_title: str) -> Dict[str, str]:
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
            if re.search("steps", subpod['@title']):
                output[subpod['@title']] = subpod['plaintext']
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

        # Check if 'pod' is a list or a dictionary
        if isinstance(dirty_input['pod'], list):
            for pod in dirty_input['pod']: 
                subpod_data = pod['subpod']
                if isinstance(subpod_data, list):
                    output.update(self.process_subpod(subpod_data, pod['@title']))
                elif subpod_data.get('plaintext'):
                    output[pod['@title']] = subpod_data['plaintext']
        else: # 'pod' is a single dictionary
            pod = dirty_input['pod'] 
            subpod_data = pod['subpod']
            if isinstance(subpod_data, list):
                output.update(self.process_subpod(subpod_data, pod['@title']))
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
            show_steps_input = await self.find_steps_input(input_string)
            configs.update(show_steps_input)
        
        response = await self._make_request("query", input_string, **configs, **kwargs)
        doc = await self._parse_xml(response.content)
        
        return doc['queryresult']


def WolframAlpha(query: str, show_steps: bool = False, raw: bool = False):
    """
    Sends a query to the Wolfram Alpha Full API. Wolfram Alpha can answer simple facts to hard math questions.
    
    Args:
        input_string: The input string for the query.
        show_steps: Whether to show the steps or not.
        raw: Whether to return the raw output. Use this when the cleaned output doesn't work.
        
    Returns:
        A dictionary representing the query result.
    """
    client = WolframAlphaFullAPI(json.load(open("config.json"))['WolframAPI'])
    
    try:
        loop = asyncio.get_running_loop()
        output = client.clean_up(loop.run_until_complete(client.query(query, show_steps)))
    except RuntimeError:
        output = client.clean_up(asyncio.run(client.query(query, show_steps)))
    
    logging.info(output)
    
    if raw:
        return query
    return output