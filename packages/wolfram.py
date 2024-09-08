import json
import wolframalpha
import logging

def wolfram(query: str):
    """
    Queries the Wolfram Alpha API and returns the text result.

    This function uses the Wolfram Alpha API to answer a given query 
    and returns the textual representation of the first result. 

    Args:
        query (str): The query to be sent to Wolfram Alpha.

    Returns:
        str: The text result from Wolfram Alpha.
    """
    client = wolframalpha.Client(json.load(open('config.json'))['WolframAPI'])
    res = client.query(query)
    result = next(res.results).text
    
    logging.info(result)
    return result
