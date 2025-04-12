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
    async def weather(city_in):
        async with python_weather.Client() as client:
            current_weather = await client.get(city_in)
            
            output = ""
            output += "Temperature: " + str(current_weather.temperature) + "°C\n"
            output += "Humidity: " + str(current_weather.humidity) + "%\n"
            output += "Wind Speed: " + str(current_weather.wind_speed) + " km/h\n"
            output += "Wind Direction: " + str(current_weather.wind_direction) + "\n"
            output += "Description: " + str(current_weather.description) + "\n"
            output += "Precipitation: " + str(current_weather.precipitation) + " mm\n"
            output += "Visibility: " + str(current_weather.visibility) + " km\n"
            output += "Pressure: " + str(current_weather.pressure) + " mbar\n"
            output += "Country: " + str(current_weather.country)
            
            logging.info(f"\n{output}")
            return output

    loop = asyncio.get_running_loop() 
    return loop.run_until_complete(weather(city))