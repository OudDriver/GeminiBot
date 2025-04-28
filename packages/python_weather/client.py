from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlunparse

import httpx

from packages.python_weather.enums import (
    DistanceUnit,
    PressureUnit,
    SpeedUnit,
)
from packages.python_weather.errors import InvalidTimeError, WeatherAPIError
from packages.python_weather.forecast import (
    Astronomy,
    ChanceOf,
    CurrentForecast,
    DailyCondition,
    Forecast,
    HourlyForecast,
    NearestArea,
)
from packages.python_weather.type import (
    Direction,
    Distance,
    Precipitation,
    Pressure,
    Speed,
    Temperature,
    UltravioletIndex,
    WeatherKind,
    Wind,
)

if TYPE_CHECKING:
    from types import TracebackType

    from packages.python_weather.enums import Locale


class Client:
    """A client object for getting the forecast."""

    FORMAT_STRING_FOR_LOCAL_OBS = "%Y-%m-%d %I:%M %p"

    def __init__(
            self,
            locale: Locale | None = None,
            client: httpx.AsyncClient | None = None,
            scheme: str | None = None,
            timeout: int = 5,
    ) -> None:
        """Initializes the client.

        Args:
            locale: The language to use. If not filled, it will default to English.
            client: A httpx.AsyncClient object. If none, it will use its own.
            scheme: A custom scheme. If left empty, it will use https.
            timeout: The time for a timeout. Defaults to 5 seconds.
        """
        self.client = client if client is not None else httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        )
        self.subdomain = locale.value if locale is not None else "en"
        self.sld = "wttr"
        self.tld = "in"
        self.scheme = scheme if scheme is not None else "https"

    async def get_weather(self, city: str) -> Forecast:
        """Fetches the current weather forecast for a specific location.

        Args:
            city: The city to look up

        Returns:
            A CurrentForecast object showing the current forecast, duh.
        """
        response_json = await self._query(city)
        return self._get_forecast_from_response(response_json)

    @staticmethod
    def _construct_domain(subdomain: str | Iterable[str], sld: str, tld: str) -> str:
        """Constructs a domain.

        Args:
            subdomain: The subdomain to give. It may be a list of string
                       or a simple string.
            sld: The domain (or the second-level domain).
            tld: The top-level domain.

        Returns:
            a
        """
        if isinstance(subdomain, Iterable) and not isinstance(subdomain, str):
            sub = ".".join(subdomain)
        elif isinstance(subdomain, str):
            sub = subdomain
        else:
            msg = (
                f"Expected 'str' or 'Iterable' that is not an 'str'. "
                f"Got {type(subdomain)}"
            )
            raise TypeError(msg)
        return f"{sub}.{sld}.{tld}"

    async def _query(self, city: str) -> dict:
        """Fetches a weather forecast for a specific location.

        Args:
            city: The city to look up

        Returns:
            A JSON response object.
        """
        query_params: dict[str, str] = {
            "format": "j1",
        }
        encoded_query_params = urlencode(query_params)
        url_components: tuple[str, str, str, str, str, str] = (
            self.scheme,
            self._construct_domain(self.subdomain, self.sld, self.tld),
            city,
            "",
            encoded_query_params,
            "",
        )

        url = urlunparse(url_components)

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Log the specific status code and error message
            msg = f"API returned error {e.response.status_code} for {url}"
            raise WeatherAPIError(msg) from e
        except httpx.RequestError as e:
            # Log the specific request error
            msg = f"An error occurred while requesting {e.request.url}: {e}"
            raise WeatherAPIError(msg) from e
        except Exception as e:
            # Catch potential json decoding errors or other unexpected issues
            msg = f"An unexpected error occurred during the API request: {e}"
            raise WeatherAPIError(msg) from e

    def _get_forecast_from_response(self, response: dict) -> Forecast:
        forecast = Forecast()
        forecast.current_condition = self._get_current_condition_from_response(
            response["current_condition"],
        )
        forecast.daily_condition = self._get_daily_conditions(response["weather"])
        forecast.nearest_area = self._get_nearest_area(response["nearest_area"][0])
        return forecast

    def _get_current_condition_from_response(
            self,
            response: dict,
    ) -> CurrentForecast:
        response = response[0]
        forecast = CurrentForecast()

        forecast.uv_index = UltravioletIndex(int(response["uvIndex"]))
        forecast.cloud_cover_percentage = int(response["cloudcover"])
        forecast.humidity = int(response["humidity"])
        forecast.precipitation = Precipitation(float(response["precipMM"]))
        forecast.last_local_observation_datetime = datetime.strptime(  # noqa: DTZ007
            response["localObsDateTime"],
            self.FORMAT_STRING_FOR_LOCAL_OBS,
        )
        forecast.pressure = Pressure(
            response["pressure"],
            PressureUnit.MILLIBAR,
        )
        forecast.wind = Wind(
            Direction(
                int(response["winddirDegree"]),
            ),
            Speed(
                int(response["windspeedKmph"]),
                SpeedUnit.KILOMETERS_PER_HOUR,
            ),
        )
        forecast.visibility = Distance(
            response["visibilityMiles"],
            DistanceUnit.MILES,
        )
        forecast.weather_description = WeatherKind(
            int(response["weatherCode"]),
            response["weatherDesc"][0]["value"],
            response[f"lang_{self.subdomain}"][0]["value"]
            if self.subdomain != "en" else None,
        )
        forecast.temperature = Temperature(
            int(response["temp_C"]),
        )
        forecast.feels_like_temperature = Temperature(
            int(response["FeelsLikeC"]),
        )

        return forecast

    def _get_hourly_forecast(
            self,
            response: dict,
    ) -> HourlyForecast:
        forecast = HourlyForecast()

        forecast.uv_index = UltravioletIndex(int(response["uvIndex"]))
        forecast.cloud_cover_percentage = int(response["cloudcover"])
        forecast.humidity = int(response["humidity"])
        forecast.precipitation = Precipitation(float(response["precipMM"]))
        forecast.pressure = Pressure(
            response["pressure"],
            PressureUnit.MILLIBAR,
        )
        forecast.wind = Wind(
            Direction(
                int(response["winddirDegree"]),
            ),
            Speed(
                int(response["windspeedKmph"]),
                SpeedUnit.KILOMETERS_PER_HOUR,
            ),
        )
        forecast.visibility = Distance(
            response["visibilityMiles"],
            DistanceUnit.MILES,
        )
        forecast.weather_description = WeatherKind(
            int(response["weatherCode"]),
            response["weatherDesc"][0]["value"],
            response[f"lang_{self.subdomain}"][0]["value"]
            if self.subdomain != "en" else None,
        )
        forecast.temperature = Temperature(
            int(response["tempC"]),
        )
        forecast.feels_like_temperature = Temperature(
            int(response["FeelsLikeC"]),
        )
        forecast.dew_point_temperature = Temperature(int(response["DewPointC"]))
        forecast.heat_index_temperature = Temperature(int(response["HeatIndexC"]))
        forecast.wind_chill_temperature = Temperature(int(response["WindChillC"]))
        forecast.wind_gust_speed = Speed(
            int(response["WindGustKmph"]),
            SpeedUnit.KILOMETERS_PER_HOUR,
        )

        chances_of = ChanceOf()
        chances_of.fog = int(response["chanceoffog"])
        chances_of.frost = int(response["chanceoffrost"])
        chances_of.high_temperature = int(response["chanceofhightemp"])
        chances_of.overcast = int(response["chanceofovercast"])
        chances_of.rain = int(response["chanceofrain"])
        chances_of.remaining_dry = int(response["chanceofremdry"])
        chances_of.snow = int(response["chanceofsnow"])
        chances_of.sunshine = int(response["chanceofsunshine"])
        chances_of.thunder =  int(response["chanceofthunder"])
        chances_of.windy = int(response["chanceofwindy"])

        forecast.chance_of = chances_of
        forecast.time = self._create_datetime_from_special_time_string(
            response["time"],
        )

        return forecast

    @staticmethod
    def _create_datetime_from_special_time_string(time_str: str) -> datetime:
        """Creates a datetime object from a string.

        Only works with strings like '0', '300', '900', '1200', '2100'.

        The string is interpreted as HHMM, where the integer value is formatted
        to a 4-digit string before parsing.

        Args:
            time_str: The input time string (e.g., '0', '300', '1200').

        Returns:
            A datetime object representing the time on 1900-01-01

        Raises:
            An InvalidTimeError if the input string has invalid formatting.
        """
        try:
            time_int = int(time_str)

            # Format the integer as a 4-digit string with leading zeros
            formatted_time_str = f"{time_int:04d}"

            return datetime.strptime(formatted_time_str, "%H%M")  # noqa: DTZ007


        except ValueError as e:
            msg = f"Error parsing string '{time_str}': {e}"
            raise InvalidTimeError(msg) from e

    @staticmethod
    def _get_astronomy_data(data: dict[str, str]) -> Astronomy:
        """Gets and creates astronomy data for each day.

        Args:
            data: The data given, usually the first element of the "astronomy" array

        Returns:
            An Astronomy object.
        """
        format_string = "%I:%M %p"

        moonrise_data = data["moonrise"]
        moonset_data = data["moonset"]
        sunrise_data = data["sunrise"]
        sunset_data = data["sunset"]

        temp_dt_moonrise = datetime.strptime(moonrise_data, format_string)  # noqa: DTZ007
        temp_dt_moonset = datetime.strptime(moonset_data, format_string)  # noqa: DTZ007
        temp_dt_sunrise = datetime.strptime(sunrise_data, format_string)  # noqa: DTZ007
        temp_dt_sunset = datetime.strptime(sunset_data, format_string)  # noqa: DTZ007

        astronomy_data = Astronomy()
        astronomy_data.moon_illumination_percentage = int(data["moon_illumination"])
        astronomy_data.moon_phase = data["moon_phase"]

        astronomy_data.moonrise = time(
            temp_dt_moonrise.hour,
            temp_dt_moonrise.minute,
        )
        astronomy_data.moonset = time(
            temp_dt_moonset.hour,
            temp_dt_moonset.minute,
        )
        astronomy_data.sunrise = time(
            temp_dt_sunrise.hour,
            temp_dt_sunrise.minute,
        )
        astronomy_data.sunset = time(
            temp_dt_sunset.hour,
            temp_dt_sunset.minute,
        )

        return astronomy_data

    def _get_single_daily_condition(
            self,
            data: dict,
    ) -> DailyCondition:
        """Gets the daily condition for one day.

        Args:
            data: An element from the "weather" key
        """
        date_of_condition_str = data["date"]
        date_of_condition = date.fromisoformat(date_of_condition_str)

        daily_condition = DailyCondition()
        daily_condition.astronomy = self._get_astronomy_data(data["astronomy"][0])
        daily_condition.average_temp = Temperature(int(data["avgtempC"]))
        daily_condition.date_of_condition = date_of_condition
        daily_condition.hourly_weather = [
            self._get_hourly_forecast(hourly) for hourly in data["hourly"]
        ]

        return daily_condition

    def _get_daily_conditions(
            self,
            data: list[dict],
    ) -> list[DailyCondition]:
        return [self._get_single_daily_condition(one_day) for one_day in data]

    @staticmethod
    def _get_nearest_area(
            data: dict[str, list[dict[str, str]] | str],
    ) -> NearestArea:
        nearest_area = NearestArea()

        nearest_area.area_name = data["areaName"][0]["value"]
        nearest_area.country = data["country"][0]["value"]
        nearest_area.latitude = float(data["latitude"])
        nearest_area.longitude = float(data["longitude"])
        nearest_area.region = data["region"][0]["value"]

        return nearest_area

    async def __aenter__(self) -> Client:
        """Enter the async context manager."""
        return self

    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager."""
        await self.client.aclose()
