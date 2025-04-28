from __future__ import annotations

from enum import Enum

from packages.python_weather.errors import (
    UnsupportedTargetUnitError,
)


class DirectionName(Enum):
    """A list (not really) of directions."""

    NORTH = "N"
    NORTH_NORTHEAST = "NNE"
    NORTHEAST = "NE"
    EAST_NORTHEAST = "ENE"
    EAST = "E"
    EAST_SOUTHEAST = "ESE"
    SOUTHEAST = "SE"
    SOUTH_SOUTHEAST = "SSE"
    SOUTH = "S"
    SOUTH_SOUTHWEST = "SSW"
    SOUTHWEST = "SW"
    WEST_SOUTHWEST = "WSW"
    WEST = "W"
    WEST_NORTHWEST = "WNW"
    NORTHWEST = "NW"
    NORTH_NORTHWEST = "NNW"

    def __str__(self) -> str:
        """Returns a pretty name.

        Replaces underscores with whitespaces.
        Capitalizes only the first letter.
        """
        return self.name.replace("_", " ").title()


class UltravioletRiskType(Enum):
    """An enums of ultraviolet types."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"
    UNKNOWN = None

    def __str__(self) -> str:
        """Returns a pretty name.

        Replaces underscores with whitespaces.
        Capitalizes only the first letter.
        """
        return self.name.replace("_", " ").title()


class Locale(Enum):
    """Supported locales/languages."""

    AFRIKAANS = "af"
    AMHARIC = "am"
    ARABIC = "ar"
    ARMENIAN = "hy"
    AZERBAIJANI = "az"
    BANGLA = "bn"
    BASQUE = "eu"
    BELARUSIAN = "be"
    BOSNIAN = "bs"
    BULGARIAN = "bg"
    CATALAN = "ca"
    CHINESE_SIMPLIFIED = "zh"
    CHINESE_SIMPLIFIED_CHINA = "zh-cn"
    CHINESE_TRADITIONAL_TAIWAN = "zh-tw"
    CROATIAN = "hr"
    CZECH = "cs"
    DANISH = "da"
    DUTCH = "nl"
    ENGLISH = "en"
    ESPERANTO = "eo"
    ESTONIAN = "et"
    FINNISH = "fi"
    FRENCH = "fr"
    FRISIAN = "fy"
    GALICIAN = "gl"
    GEORGIAN = "ka"
    GERMAN = "de"
    GREEK = "el"
    HINDI = "hi"
    HIRI_MOTU = "ho"
    HUNGARIAN = "hu"
    ICELANDIC = "is"
    INDONESIAN = "id"
    INTERLINGUA = "ia"
    IRISH = "ga"
    ITALIAN = "it"
    JAPANESE = "ja"
    JAVANESE = "jv"
    KAZAKH = "kk"
    KISWAHILI = "sw"
    KOREAN = "ko"
    KYRGYZ = "ky"
    LATVIAN = "lv"
    LITHUANIAN = "lt"
    MACEDONIAN = "mk"
    MALAGASY = "mg"
    MALAYALAM = "ml"
    MARATHI = "mr"
    NORWEGIAN_BOKMAL = "nb"
    NORWEGIAN_NYNORSK = "nn"
    OCCITAN = "oc"
    PERSIAN = "fa"
    POLISH = "pl"
    PORTUGUESE = "pt"
    PORTUGUESE_BRAZIL = "pt-br"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SERBIAN = "sr"
    SERBIAN_LATIN = "sr-lat"
    SLOVAK = "sk"
    SLOVENIAN = "sl"
    SPANISH = "es"
    SWEDISH = "sv"
    TAMIL = "ta"
    TELUGU = "te"
    THAI = "th"
    TURKISH = "tr"
    UKRAINIAN = "uk"
    UZBEK = "uz"
    VIETNAMESE = "vi"
    WELSH = "cy"
    ZULU = "zu"

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value


class SpeedUnit(Enum):
    """Enum for supported speed units."""

    METERS_PER_SECOND = ("m/s", 1.0)
    KILOMETERS_PER_HOUR = ("km/h", 1000.0 / 3600.0)
    MILES_PER_HOUR = ("mph", 1609.34 / 3600.0)
    FEET_PER_SECOND = ("ft/s", 0.3048)
    KNOTS = ("knots", 1852.0 / 3600.0)
    SPEED_OF_LIGHT = ("c", 299792458.0)

    @property
    def unit_string(self) -> str:
        """Returns the standard string representation for the unit."""
        return self.value[0]

    @property
    def conversion_factor_to_mps(self) -> float:
        """Returns the factor to multiply by to get meters per second."""
        return self.value[1]

    @classmethod
    def from_string(cls, unit_str: str) -> SpeedUnit:
        """Looks up a SpeedUnit enum member by its string representation."""
        unit_str_lower = unit_str.lower()
        for member in cls:
            if member.unit_string.lower() == unit_str_lower:
                return member
        raise UnsupportedTargetUnitError(unit_str, [m.unit_string for m in cls])

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value[0]


class TemperatureUnit(Enum):
    """Enum for temperature units."""
    CELSIUS = ("°C", 1.0, 0.0)
    FAHRENHEIT = ("°F", 9/5, -32)
    KELVIN = ("K", 1.0, -273.15)

    @property
    def unit_string(self) -> str:
        """Returns the standard string representation for the unit."""
        return self.value[0]

    @property
    def conversion_factor_to_celcius(self) -> float:
        """Returns the factor to multiply by to get meters."""
        return self.value[1]

    @property
    def addition_offset_factor_to_celcius(self) -> float:
        """Returns the factor to multiply by to get meters."""
        return self.value[2]

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value[0]


class DistanceUnit(Enum):
    """Enum for supported distance units."""

    METERS = ("m", 1.0)
    KILOMETERS = ("km", 1000.0)
    MILES = ("mi", 1609.34)
    FEET = ("ft", 0.3048)
    YARDS = ("yd", 0.9144)
    INCHES = ("in", 0.0254)
    NAUTICAL_MILES = ("nmi", 1852.0)

    @property
    def unit_string(self) -> str:
        """Returns the standard string representation for the unit."""
        return self.value[0]

    @property
    def conversion_factor_to_meters(self) -> float:
        """Returns the factor to multiply by to get meters."""
        return self.value[1]

    @classmethod
    def from_string(cls, unit_str: str) -> DistanceUnit:
        """Looks up a DistanceUnit enum member by its string representation."""
        unit_str_lower = unit_str.lower()
        for member in cls:
            if member.unit_string.lower() == unit_str_lower:
                return member
        raise UnsupportedTargetUnitError(unit_str, [m.unit_string for m in cls])

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value[0]


class WeatherKindType(Enum):
    """An enum for the kinds of weather."""

    SUNNY = 113
    PARTLY_CLOUDY = 116
    CLOUDY = 119
    VERY_CLOUDY = 122
    FOG = 143
    LIGHT_SHOWERS = 176
    LIGHT_SLEET_SHOWERS = 179
    LIGHT_SLEET = 182
    THUNDERY_SHOWERS = 200
    LIGHT_SNOW = 227
    HEAVY_SNOW = 230
    LIGHT_RAIN = 266
    HEAVY_SHOWERS = 299
    HEAVY_RAIN = 302
    LIGHT_SNOW_SHOWERS = 323
    HEAVY_SNOW_SHOWERS = 335
    THUNDERY_HEAVY_RAIN = 389
    THUNDERY_SNOW_SHOWERS = 392

    def __str__(self) -> str:
        """Returns a pretty name.

        Replaces underscores with whitespaces.
        Capitalizes only the first letter.
        """
        return self.name.replace("_", " ").title()


class PressureUnit(Enum):
    """A class enum for pressure units."""
    PASCAL = ("Pa", 1.0)
    MILLIBAR = ("mbar", 100.0)
    BAR = ("bar", 100000.0)
    ATMOSPHERE = ("atm", 101325.0)
    TORR = ("Torr", 133.322)
    POUNDS_PER_SQUARE_INCH = ("psi", 6894.76)
    BARYE = ("Ba", 0.1)

    @property
    def unit_string(self) -> str:
        """Returns the standard string representation for the unit."""
        return self.value[0]

    @property
    def conversion_factor_to_pascal(self) -> float:
        """Returns the factor to multiply by to get pascal."""
        return self.value[1]

    @classmethod
    def from_string(cls, unit_str: str) -> PressureUnit:
        """Looks up a PressureUnit enum member by its string representation."""
        unit_str_lower = unit_str.lower()
        for member in cls:
            if member.unit_string.lower() == unit_str_lower:
                return member
        raise UnsupportedTargetUnitError(unit_str, [m.unit_string for m in cls])

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value[0]


class PrecipitationUnit(Enum):
    """A class enum for pressure units."""
    MILLIMETER = ("mm", 1.0)
    LITER_PER_SQ_METER = ("liter/m²", 1.0)
    INCHES = ("in", 25.4)

    @property
    def unit_string(self) -> str:
        """Returns the standard string representation for the precipitation unit."""
        return self.value[0]

    @property
    def conversion_factor_to_millimeter(self) -> float:
        """Returns the factor to multiply by to get millimeter."""
        return self.value[1]

    @classmethod
    def from_string(cls, unit_str: str) -> PrecipitationUnit:
        """Looks up a PrecipitationUnit enum member by its string representation."""
        unit_str_lower = unit_str.lower()
        for member in cls:
            if member.unit_string.lower() == unit_str_lower:
                return member
        raise UnsupportedTargetUnitError(unit_str, [m.unit_string for m in cls])

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value[0]


class PowerPerUnitAreaUnit(Enum):
    """A class enum for units for power per unit area."""
    WATT_PER_SQ_METER = ("W/m²", 1.0)
    KILOWATT_PER_SQ_METER = ("kW/m²", 1000.0)
    BTU_PER_HOUR_PER_SQ_FOOT = ("BTU/(hr·ft²)", 3.15459074504)
    BTU_PER_MINUTE_PER_SQ_FOOT = ("BTU/(hr·ft²)", 189.148815792)
    LANGLEY_PER_MINUTE = ("Ly/min", 697.3)
    # noinspection PyUnresolvedReferences
    CALORIE_PER_SQ_CENTIMETER_PER_MINUTE = (
        "cal/(cm²·min)",
        LANGLEY_PER_MINUTE[1], # The same as Ly/min
    )

    @property
    def unit_string(self) -> str:
        """Returns the standard string representation for the power per unit area."""
        return self.value[0]

    @property
    def conversion_factor_to_watt_per_sq_meter(self) -> float:
        """Returns the factor to multiply by to get Watt per Square Meter (W/m²)."""
        return self.value[1]

    def __str__(self) -> str:
        """Returns a pretty name.

        Uses the value of the enums.

        Returns:
            The unit.
        """
        return self.value[0]
