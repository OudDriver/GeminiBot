import asyncio
import logging

import nest_asyncio

import packages.python_weather
from packages.utilities.file_utils import save_temp_config

nest_asyncio.apply()
logger = logging.getLogger(__name__)


async def weather(city_in: str) -> dict[str: float | str] | None:
    """Fetches current weather data for a given city and returns it as a dictionary.

    Args:
        city_in (str): The name of the city.

    Returns:
        dict: A dictionary containing various weather parameters,
        or None if an error occurs.
    """
    weather_data = {} # Initialize an empty dictionary

    try:
        async with packages.python_weather.Client() as client:
            weather_condition = await client.get_weather(city_in)
            current_condition = weather_condition.current_condition

            weather_data["Humidity"] = current_condition.humidity
            weather_data["Temperature"] = str(current_condition.temperature)
            weather_data["Wind"] = str(current_condition.wind)
            weather_data["Description"] = str(current_condition.weather_description)
            weather_data["Precipitation"] = str(current_condition.precipitation)
            weather_data["Visibility"] = str(current_condition.visibility)
            weather_data["Pressure"] = str(current_condition.pressure)
            weather_data["Country"] = weather_condition.nearest_area.country
            weather_data["City"] = city_in
            weather_data["Latitude"] = weather_condition.nearest_area.latitude
            weather_data["Longitude"] = weather_condition.nearest_area.longitude


        # Log the dictionary (or a representation of it)
        logger.info(f"Successfully fetched weather data for {city_in}: {weather_data}")

        # Return the dictionary
        return weather_data

    except packages.python_weather.errors.WeatherAPIError:
        logger.exception(
            f"Error fetching weather for {city_in}: "
            f"Could not find location or a request error occurred.",
        )
        raise

    except Exception:
        logger.exception(f"Error fetching weather for {city_in}")
        raise


def get_weather(city: str) -> dict | str:
    """Gets the weather of a city.

    Args:
        city: The city to get the weather.

    Returns:
        An output of the temperature now, and what the weather is going to be.

    """
    loop = asyncio.get_running_loop()
    try:
        weather_output = loop.run_until_complete(weather(city))

    except packages.python_weather.errors.WeatherAPIError:
        return (
            f"Error fetching weather for {city}: "
            f"Could not find location or a request error occurred."
        )

    except Exception:
        return (
            f"An unexpected error occurred while trying to "
            f"fetch the weather for {city}."
        )

    save_temp_config(
        tool_use={
            "name": "Get Weather",
            "input": city,
            "output": weather_output,
        },
    )
    return weather_output
