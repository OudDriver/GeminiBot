import python_weather
import asyncio
import nest_asyncio
import logging

nest_asyncio.apply()

def get_weather(city: str):
    """Gets the weather of a city.
    
    Args:
        city: The city to get the weather.
    
    Returns:
        An output of the temperature now, and what the weather is going to be.
    """
    async def weather(cityin):
        # declare the client. the measuring unit used defaults to the metric system (celcius, km/h, etc.)
        async with python_weather.Client(unit=python_weather.METRIC) as client:
            weather = await client.get(cityin)
            
            output = ""
            output += "Temperature: " + str(weather.temperature) + "°C\n"
            output += "Humidity: " + str(weather.humidity) + "%\n"
            output += "Wind Speed: " + str(weather.wind_speed) + " km/h\n"
            output += "Wind Direction: " + str(weather.wind_direction) + "\n"
            output += "Description: " + str(weather.description) + "\n"
            output += "Precipitation: " + str(weather.precipitation) + " mm\n"
            output += "Visibility: " + str(weather.visibility) + " km\n"
            output += "Pressure: " + str(weather.pressure) + " mbar\n"
            output += "Country: " + str(weather.country)
            
            logging.info(f"\n{output}")
            return output

    loop = asyncio.get_running_loop() 
    return loop.run_until_complete(weather(city))