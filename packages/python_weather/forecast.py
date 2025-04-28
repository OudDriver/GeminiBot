from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime, time

    from packages.python_weather.type import (
        Distance,
        PowerPerUnitArea,
        Precipitation,
        Pressure,
        Speed,
        Temperature,
        UltravioletIndex,
        WeatherKind,
        Wind,
    )


class ChanceOf:
    """A class to store the chances of a future event, such as rain or snow."""
    fog: int
    frost: int
    high_temperature: int
    overcast: int
    rain: int
    remaining_dry: int
    snow: int
    sunshine: int
    thunder: int
    windy: int


class Forecast:
    """A base response object."""
    current_condition: CurrentForecast
    daily_condition: list[DailyCondition]
    nearest_area: NearestArea


class BaseForecast:
    """A base forecast object."""
    feels_like_temperature: Temperature
    cloud_cover_percentage: int
    humidity: int
    precipitation: Precipitation
    pressure: Pressure
    uv_index: UltravioletIndex
    visibility: Distance
    weather_description: WeatherKind
    temperature: Temperature
    wind: Wind


class NearestArea:
    """Data about the nearest area from the response."""
    area_name: str
    country: str
    latitude: float
    longitude: float
    region: str


class CurrentForecast(BaseForecast):
    """An object for the current forecast."""
    last_local_observation_datetime: datetime


class HourlyForecast(BaseForecast):
    """An object for hourly forecast."""
    dew_point_temperature: Temperature
    heat_index_temperature: Temperature
    wind_chill_temperature: Temperature
    wind_gust_speed: Speed
    diffuse_radiation: PowerPerUnitArea
    shortwave_radiation: PowerPerUnitArea
    chance_of: ChanceOf
    time: datetime


class Astronomy:
    """Shows data related to astronomy (e.g. moon phase)."""
    moon_illumination_percentage: int
    moon_phase: str
    moonrise: time
    moonset: time
    sunrise: time
    sunset: time


class DailyCondition:
    """An object to show a condition for one day."""
    astronomy: Astronomy
    average_temp: Temperature
    date_of_condition: date
    hourly_weather: list[HourlyForecast]
