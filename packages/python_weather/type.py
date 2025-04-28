from __future__ import annotations

from typing import ClassVar

from packages.python_weather.enums import (
    DirectionName,
    DistanceUnit,
    PowerPerUnitAreaUnit,
    PrecipitationUnit,
    PressureUnit,
    SpeedUnit,
    TemperatureUnit,
    UltravioletRiskType,
    WeatherKindType,
)
from packages.python_weather.errors import (
    InvalidDirectionTypeError,
    InvalidDistanceValueTypeError,
    InvalidPowerPerUnitAreaValueTypeError,
    InvalidPrecipitationValueTypeError,
    InvalidPressureValueTypeError,
    InvalidSpeedTypeError,
    InvalidTemperatureValueTypeError,
    InvalidUnitTypeError,
    InvalidUVTypeError,
    InvalidWeatherKindIDError,
    InvalidWeatherKindTypeError,
    InvalidWindDirectionTypeError,
    InvalidWindSpeedTypeError,
)


class Direction:
    """An object representing directions."""

    degrees: float
    name: DirectionName

    _NAME_TO_DEGREES: ClassVar[dict[DirectionName, float]] = {
        DirectionName.NORTH: 0.0,
        DirectionName.NORTH_NORTHEAST: 22.5,
        DirectionName.NORTHEAST: 45.0,
        DirectionName.EAST_NORTHEAST: 67.5,
        DirectionName.EAST: 90.0,
        DirectionName.EAST_SOUTHEAST: 112.5,
        DirectionName.SOUTHEAST: 135.0,
        DirectionName.SOUTH_SOUTHEAST: 157.5,
        DirectionName.SOUTH: 180.0,
        DirectionName.SOUTH_SOUTHWEST: 202.5,
        DirectionName.SOUTHWEST: 225.0,
        DirectionName.WEST_SOUTHWEST: 247.5,
        DirectionName.WEST: 270.0,
        DirectionName.WEST_NORTHWEST: 292.5,
        DirectionName.NORTHWEST: 315.0,
        DirectionName.NORTH_NORTHWEST: 337.5,
    }

    _DEGREES_TO_NAME: ClassVar[dict[float, DirectionName]] = {
        0.0: DirectionName.NORTH,
        22.5: DirectionName.NORTH_NORTHEAST,
        45.0: DirectionName.NORTHEAST,
        67.5: DirectionName.EAST_NORTHEAST,
        90.0: DirectionName.EAST,
        112.5: DirectionName.EAST_SOUTHEAST,
        135.0: DirectionName.SOUTHEAST,
        157.5: DirectionName.SOUTH_SOUTHEAST,
        180.0: DirectionName.SOUTH,
        202.5: DirectionName.SOUTH_SOUTHWEST,
        225.0: DirectionName.SOUTHWEST,
        247.5: DirectionName.WEST_SOUTHWEST,
        270.0: DirectionName.WEST,
        292.5: DirectionName.WEST_NORTHWEST,
        315.0: DirectionName.NORTHWEST,
        337.5: DirectionName.NORTH_NORTHWEST,
    }

    def _degrees_to_name(self, degrees: float) -> DirectionName:
        """Converts a degree value (0-360) to the closest standard direction names.

        Args:
            degrees: The degree value. It will be normalized to 0-360.

        Returns:
            The closest standard direction name DirectionType.
        """
        normalized_degrees = float(degrees) % 360.0

        closest_direction_degrees = None
        min_diff = 361

        for standard_degrees in self._DEGREES_TO_NAME:
            diff1 = abs(normalized_degrees - standard_degrees)
            diff2 = 360 - diff1
            current_diff = min(diff1, diff2)

            if current_diff < min_diff:
                min_diff = current_diff
                closest_direction_degrees = standard_degrees
            elif (
                current_diff == min_diff
                and standard_degrees > closest_direction_degrees
            ):
                closest_direction_degrees = standard_degrees

        return self._DEGREES_TO_NAME[closest_direction_degrees]

    def _name_to_degrees(self, name: DirectionName) -> float:
        """Convert DirectionType names to degree.

        Args:
            name: The DirectionType type.

        Returns:
            The degree value.
        """
        return self._NAME_TO_DEGREES[name]

    def __init__(self, value: float | DirectionName) -> None:
        """Initializes a Direction object.

        Args:
            value: The direction, which can be:
                   - A number (float or int) representing degrees (0-360)
                     clockwise from North.
                   - A DirectionType.

        Raises:
            InvalidDirectionTypeError: If the input value is not a number
            or a DirectionType.
        """
        if isinstance(value, (float, int)):
            self.degrees = float(value) % 360.0
            self.name = self._degrees_to_name(value)
        elif isinstance(value, DirectionName):
            self.degrees = self._name_to_degrees(value)
            self.name = value
        else:
            # If the input type is wrong, raise an error
            raise InvalidDirectionTypeError(type(value), (float, DirectionName))

    def __str__(self) -> str:
        """Returns a pretty name."""
        return str(f"{self.degrees}°")


class UltravioletIndex:
    """A class for ultraviolet index."""

    _RISK_TO_INDEX: ClassVar[dict[UltravioletRiskType, int | None]] = {
        UltravioletRiskType.UNKNOWN: None,
        UltravioletRiskType.LOW: 1,
        UltravioletRiskType.MODERATE: 4,
        UltravioletRiskType.HIGH: 7,
        UltravioletRiskType.VERY_HIGH: 9,
        UltravioletRiskType.EXTREME: 11,
    }

    def __init__(self, value: int | UltravioletRiskType) -> None:
        """Initialize a UV index object.

        Args:
            value: The index, which can be
                   A number (int) representing the index.
                   A UltravioletType.

        Raises:
            InvalidUVTypeError: If the input value is not a number
            or a UltravioletRiskType.
        """
        if isinstance(value, int):
            self.index = value
            self.risk_level = self._index_to_risk(value)
        elif isinstance(value, UltravioletRiskType):
            self.index = self._risk_to_index(value)
            self.risk_level = value
        else:
            raise InvalidUVTypeError(type(value), [int, UltravioletRiskType])

    @staticmethod
    def _index_to_risk(uv_index: int) -> UltravioletRiskType:
        """Determines the UV risk level based on the numerical value.

        Args:
            uv_index: The UV Index value.

        Returns:
            The risk level (Low, Moderate, High, Very High, Extreme)
            via the UltravioletRiskType object.

        Raises:
            An InvalidUVTypeError if the uv_index type isn't an integer.

        """
        if not isinstance(uv_index, int):
            raise InvalidUVTypeError(type(uv_index), [int])

        if 0 <= uv_index <= 2:  # noqa: PLR2004
            return UltravioletRiskType.LOW
        if 3 <= uv_index <= 5:  # noqa: PLR2004
            return UltravioletRiskType.MODERATE
        if 6 <= uv_index <= 7:  # noqa: PLR2004
            return UltravioletRiskType.HIGH
        if 8 <= uv_index <= 10:  # noqa: PLR2004
            return UltravioletRiskType.VERY_HIGH
        if uv_index >= 11:  # noqa: PLR2004
            return UltravioletRiskType.EXTREME
        return UltravioletRiskType.UNKNOWN

    def _risk_to_index(self, uv_risk: UltravioletRiskType) -> int:
        """Determines the UV risk level based on the numerical value.

        Args:
            uv_risk: The UV Index value.

        Returns:
            The risk level (Low, Moderate, High, Very High, Extreme)
            via the UltravioletRiskType object.

        Raises:
            An InvalidUVTypeError if the uv_risk type isn't an UltravioletRiskType.

        """
        if not isinstance(uv_risk, UltravioletRiskType):
            raise InvalidUVTypeError(type(uv_risk), [UltravioletRiskType])
        return self._RISK_TO_INDEX[uv_risk]

    def __str__(self) -> str:
        """Returns a pretty name."""
        return str(f"{self.index}: {self.risk_level}")


class WeatherKind:
    """A weather forecast kind. Based off code."""

    _MAPPING: ClassVar[dict[WeatherKindType, list[int]]] = {
        WeatherKindType.FOG: [248, 260, 143],
        WeatherKindType.LIGHT_SHOWERS: [263, 353, 176],
        WeatherKindType.LIGHT_SLEET_SHOWERS: [362, 365, 374, 179],
        WeatherKindType.LIGHT_SLEET: [185, 281, 284, 311, 314, 317, 350, 377, 182],
        WeatherKindType.THUNDERY_SHOWERS: [386, 200],
        WeatherKindType.LIGHT_SNOW: [320, 227],
        WeatherKindType.HEAVY_SNOW: [329, 332, 338, 230],
        WeatherKindType.LIGHT_RAIN: [293, 296, 266],
        WeatherKindType.HEAVY_SHOWERS: [305, 356, 299],
        WeatherKindType.HEAVY_RAIN: [308, 359, 302],
        WeatherKindType.LIGHT_SNOW_SHOWERS: [326, 368, 323],
        WeatherKindType.HEAVY_SNOW_SHOWERS: [371, 395, 335],
        WeatherKindType.SUNNY: [113],
        WeatherKindType.PARTLY_CLOUDY: [116],
        WeatherKindType.CLOUDY: [119],
        WeatherKindType.VERY_CLOUDY: [122],
        WeatherKindType.THUNDERY_HEAVY_RAIN: [389],
        WeatherKindType.THUNDERY_SNOW_SHOWERS: [392],
    }

    _WEATHER_ID_TO_NAME: ClassVar[dict[int, WeatherKindType]] = {
        248: WeatherKindType.FOG,
        260: WeatherKindType.FOG,
        263: WeatherKindType.LIGHT_SHOWERS,
        353: WeatherKindType.LIGHT_SHOWERS,
        362: WeatherKindType.LIGHT_SLEET_SHOWERS,
        365: WeatherKindType.LIGHT_SLEET_SHOWERS,
        374: WeatherKindType.LIGHT_SLEET_SHOWERS,
        185: WeatherKindType.LIGHT_SLEET,
        281: WeatherKindType.LIGHT_SLEET,
        284: WeatherKindType.LIGHT_SLEET,
        311: WeatherKindType.LIGHT_SLEET,
        314: WeatherKindType.LIGHT_SLEET,
        317: WeatherKindType.LIGHT_SLEET,
        350: WeatherKindType.LIGHT_SLEET,
        377: WeatherKindType.LIGHT_SLEET,
        386: WeatherKindType.THUNDERY_SHOWERS,
        320: WeatherKindType.LIGHT_SNOW,
        329: WeatherKindType.HEAVY_SNOW,
        332: WeatherKindType.HEAVY_SNOW,
        338: WeatherKindType.HEAVY_SNOW,
        293: WeatherKindType.LIGHT_RAIN,
        296: WeatherKindType.LIGHT_RAIN,
        305: WeatherKindType.HEAVY_SHOWERS,
        356: WeatherKindType.HEAVY_SHOWERS,
        308: WeatherKindType.HEAVY_RAIN,
        359: WeatherKindType.HEAVY_RAIN,
        326: WeatherKindType.LIGHT_SNOW_SHOWERS,
        368: WeatherKindType.LIGHT_SNOW_SHOWERS,
        371: WeatherKindType.HEAVY_SNOW_SHOWERS,
        395: WeatherKindType.HEAVY_SNOW_SHOWERS,
        113: WeatherKindType.SUNNY,
        116: WeatherKindType.PARTLY_CLOUDY,
        119: WeatherKindType.CLOUDY,
        122: WeatherKindType.VERY_CLOUDY,
        143: WeatherKindType.FOG,
        176: WeatherKindType.LIGHT_SHOWERS,
        179: WeatherKindType.LIGHT_SLEET_SHOWERS,
        182: WeatherKindType.LIGHT_SLEET,
        200: WeatherKindType.THUNDERY_SHOWERS,
        227: WeatherKindType.LIGHT_SNOW,
        230: WeatherKindType.HEAVY_SNOW,
        266: WeatherKindType.LIGHT_RAIN,
        299: WeatherKindType.HEAVY_SHOWERS,
        302: WeatherKindType.HEAVY_RAIN,
        323: WeatherKindType.LIGHT_SNOW_SHOWERS,
        335: WeatherKindType.HEAVY_SNOW_SHOWERS,
        389: WeatherKindType.THUNDERY_HEAVY_RAIN,
        392: WeatherKindType.THUNDERY_SNOW_SHOWERS,
    }

    _ALL_WEATHER_ID: tuple[int, ...] = tuple(
        {weather_id for ids in _MAPPING.values() for weather_id in ids},
    )

    def __init__(
        self,
        value: int | WeatherKindType,
        description: str | None = None,
        lang_description: str | None = None,
    ) -> None:
        """Initializes the WeatherKind object.

        Args:
            value: The value of the weather kind.
                   Could be an integer ID or a WeatherKindType.
            description: The description of the weather.
            lang_description: A description in another language
                              if given.
        """
        if isinstance(value, int):
            self.id = value
            self.name = self._id_to_name(value)
        elif isinstance(value, WeatherKindType):
            self.id = self._name_to_id(value)
            self.name = value
        else:
            raise InvalidWeatherKindTypeError(type(value), [int, WeatherKindType])

        self.description = description if description is not None else self.name
        self.lang_description = (
            lang_description if lang_description is not None else self.description
        )

    def _id_to_name(self, value: int) -> WeatherKindType | None:
        """Converts an ID to a WeatherKindType.

        Args:
            value: The integer ID.

        Returns:
            The corresponding WeatherKindType or None if the ID is not found.
        """
        name = self._WEATHER_ID_TO_NAME.get(value)

        if not name:
            raise InvalidWeatherKindIDError(value, self._ALL_WEATHER_ID)

        return name

    def _name_to_id(self, value: WeatherKindType) -> list[int]:
        """Converts a WeatherKindType to an ID.

        Args:
            value: The WeatherKindType enum value.

        Returns:
            A list of integer IDs corresponding to the given WeatherKindType.
            Returns an empty list if the WeatherKindType is not found
        """
        return self._MAPPING.get(value, [])

    def __str__(self) -> str:
        """Returns a pretty name."""
        return str(f"ID {self.id}: {self.name}.")


class Speed:
    """A class to represent and manipulate speed values with various units.

    Uses an Enum for unit management.
    """

    def __init__(
        self,
        value: float,
        unit: str | SpeedUnit = SpeedUnit.METERS_PER_SECOND,
    ) -> None:
        """Initializes a Speed object.

        Args:
            value: The value of the speed.
            unit: The unit of the speed.
                  Defaults to SpeedUnit.METERS_PER_SECOND.
                  Can be a SpeedUnit enum member or a string.

        Raises:
            An InvalidUnitTypeError if unit isn't a string or a SpeedUnit.
        """
        if not isinstance(value, (float, int)):
            raise InvalidSpeedTypeError(type(value), [int, float])

        self.value = float(value)

        if isinstance(unit, str):
            self.unit = SpeedUnit.from_string(unit)
        elif isinstance(unit, SpeedUnit):
            self.unit = unit
        else:
            raise InvalidUnitTypeError(type(unit), [str, SpeedUnit])

    def to_meters_per_second(self) -> Speed:
        """Converts the speed to meters per second."""
        return Speed(self.value * self.unit.conversion_factor_to_mps)

    def to(self, target_unit: str | SpeedUnit) -> Speed:
        """Converts the speed to the specified target unit.

        Args:
            target_unit (SpeedUnit or str): The unit to convert to.

        Returns:
            float: The speed value in the target unit.

        Raises:
            UnsupportedTargetUnitError: If the target unit string is not supported.
            InvalidUnitTypeError: If the target unit is
                                  neither a string nor a SpeedUnit.
        """
        if isinstance(target_unit, str):
            target_unit_enum = SpeedUnit.from_string(target_unit)
        elif isinstance(target_unit, SpeedUnit):
            target_unit_enum = target_unit
        else:
            raise InvalidUnitTypeError(type(target_unit), [str, SpeedUnit])

        m_per_s = self.to_meters_per_second()
        return Speed(
            m_per_s.value / target_unit_enum.conversion_factor_to_mps,
            target_unit_enum,
        )

    def __str__(self) -> str:
        """Returns a pretty name."""
        return str(f"{self.value} m/s")


class Wind:
    """A wind class."""

    def __init__(self, direction: Direction, speed: Speed | float) -> None:
        """Initializes a Wind object.

        Args:
            direction: The wind direction as a Direction.
            speed: The speed as a speed or an integer (in meter per second)

        Raises:
            InvalidWindDirectionTypeError if the type for direction is not Direction.
            InvalidWindSpeedTypeError if the type for speed
            is neither a Speed nor an int.
        """
        if not isinstance(direction, Direction):
            raise InvalidWindDirectionTypeError(type(direction), (Direction,))
        if not isinstance(speed, Speed):
            raise InvalidWindSpeedTypeError(type(speed), (Speed, float, int))

        if isinstance(speed, (float, int)):
            self.speed = Speed(float(speed))  # Already in meter per second
        if isinstance(speed, Speed):
            self.speed = speed

        self.direction = direction


    def __str__(self) -> str:
        """Returns a pretty name."""
        return str(f"{self.direction.degrees}° at {self.speed.value} m/s")


class Distance:
    """A class to represent and manipulate distance values with various units.

    Uses an Enum for unit management.
    """

    def __init__(
        self,
        value: float,
        unit: DistanceUnit | str = DistanceUnit.METERS,
    ) -> None:
        """Initializes a Distance object.

        Args:
            value: The value of the distance.
            unit: The unit of the distance.
                  Defaults to DistanceUnit.METERS.
                  Can be a DistanceUnit enum member or a string.
        """
        if not isinstance(value, (float, int)):
            InvalidDistanceValueTypeError(type(value), [float, int])
        self.value = float(value)

        if isinstance(unit, str):
            self.unit = DistanceUnit.from_string(unit)
        elif isinstance(unit, DistanceUnit):
            self.unit = unit
        else:
            raise InvalidUnitTypeError(type(unit), [str, DistanceUnit])

    def to_meters(self) -> Distance:
        """Converts the distance to meters."""
        return Distance(self.value * self.unit.conversion_factor_to_meters)

    def to(self, target_unit: str | DistanceUnit) -> Distance:
        """Converts the distance to the specified target unit.

        Args:
            target_unit (DistanceUnit or str): The unit to convert to.

        Returns:
            float: The distance value in the target unit.

        Raises:
            UnsupportedTargetUnitError: If the target unit string is not supported.
            InvalidUnitTypeError: If the target unit is
                                  neither a string nor a DistanceUnit.
        """
        if isinstance(target_unit, str):
            target_unit_enum = DistanceUnit.from_string(target_unit)
        elif isinstance(target_unit, DistanceUnit):
             target_unit_enum = target_unit
        else:
            raise InvalidUnitTypeError(type(target_unit), [str, DistanceUnit])

        meters = self.to_meters()
        return Distance(
            meters.value / target_unit_enum.conversion_factor_to_meters,
            target_unit_enum,
        )

    def __str__(self) -> str:
        """Returns a pretty name."""
        return f"{self.value} {self.unit}"


class Temperature:
    """Represents a temperature value with a specific unit."""

    def __init__(
            self,
            value: float,
            unit: TemperatureUnit = TemperatureUnit.CELSIUS,
    ) -> None:
        """Initializes a Temperature object.

        Args:
            value: The numerical temperature value.
            unit: The unit of the temperature (e.g., TemperatureUnit.CELSIUS).
        """
        if not isinstance(value, (int, float)):
            raise InvalidTemperatureValueTypeError(type(value), (int, float))
        if not isinstance(unit, TemperatureUnit):
            raise InvalidUnitTypeError(type(unit), (TemperatureUnit,))

        self.value = value
        self.unit = unit

    def to_celcius(self) -> Temperature:
        """Converts the distance to meters."""
        return Temperature(
            self.value
            * self.unit.conversion_factor_to_celcius
            + self.unit.addition_offset_factor_to_celcius,
        )

    def to(self, target_unit: TemperatureUnit) -> Temperature:
        """Converts the distance to the specified target unit.

        Args:
            target_unit: The unit to convert to.

        Returns:
            float: The distance value in the target unit.

        Raises:
            UnsupportedTargetUnitError: If the target unit string is not supported.
            InvalidUnitTypeError: If the target unit is
                                  neither a string nor a DistanceUnit.
        """
        if not isinstance(target_unit, TemperatureUnit):
            raise InvalidUnitTypeError(type(target_unit), [TemperatureUnit])
        target_unit_enum = target_unit

        celcius = self.to_celcius()
        return Temperature(
            celcius.value
            / target_unit_enum.conversion_factor_to_celcius
            - target_unit_enum.addition_offset_factor_to_celcius,
            target_unit_enum,
        )

    def __str__(self) -> str:
        """Returns a pretty name."""
        return f"{self.value} {self.unit}"


class Pressure:
    """A class to represent and manipulate pressure values with various units.

    Uses an Enum or a string input for unit management.
    """

    def __init__(
        self,
        value: float,
        unit: PressureUnit | str = PressureUnit.PASCAL,
    ) -> None:
        """Initializes a Pressure object.

        Args:
            value: The value of the pressure.
            unit: The unit of the pressure.
                  Defaults to PressureUnit.PASCAL (Pa).
                  Can be a PressureUnit enum member or a string.
        """
        if not isinstance(value, (float, int)):
            InvalidPressureValueTypeError(type(value), [float, int])
        self.value = float(value)

        if isinstance(unit, str):
            self.unit = PressureUnit.from_string(unit)
        elif isinstance(unit, PressureUnit):
            self.unit = unit
        else:
            raise InvalidUnitTypeError(type(unit), [str, PressureUnit])

    def to_pascal(self) -> Pressure:
        """Converts the distance to meters."""
        return Pressure(self.value * self.unit.conversion_factor_to_pascal)

    def to(self, target_unit: str | PressureUnit) -> Pressure:
        """Converts the pressure to the specified target unit.

        Args:
            target_unit: The unit to convert to.

        Returns:
            float: The distance value in the target unit.

        Raises:
            UnsupportedTargetUnitError: If the target unit string is not supported.
            InvalidUnitTypeError: If the target unit is
                                  neither a string nor a PressureUnit.
        """
        if isinstance(target_unit, str):
            target_unit_enum = PressureUnit.from_string(target_unit)
        elif isinstance(target_unit, PressureUnit):
            target_unit_enum = target_unit
        else:
            raise InvalidUnitTypeError(type(target_unit), [str, DistanceUnit])

        pascal = self.to_pascal()
        return Pressure(
            pascal.value / target_unit_enum.conversion_factor_to_pascal,
            target_unit_enum,
        )

    def __str__(self) -> str:
        """Returns a pretty name."""
        return f"{self.value} {self.unit}"


class Precipitation:
    """A class to represent amount of precipitation with various units.

    Uses an Enum and a string for unit management.
    """

    def __init__(
        self,
        value: float,
        unit: PrecipitationUnit | str = PrecipitationUnit.MILLIMETER,
    ) -> None:
        """Initializes a Precipitation object.

        Args:
            value: The value of the distance.
            unit: The unit of the distance.
                  Defaults to Precipitation.MILLIMETER (mm).
                  Can be a Precipitation enum member or a string.
        """
        if not isinstance(value, (float, int)):
            InvalidPrecipitationValueTypeError(type(value), [float, int])
        self.value = float(value)

        if isinstance(unit, str):
            self.unit = PrecipitationUnit.from_string(unit)
        elif isinstance(unit, PrecipitationUnit):
            self.unit = unit
        else:
            raise InvalidUnitTypeError(type(unit), [str, Precipitation])

    def to_millimeter(self) -> Precipitation:
        """Converts the distance to meters."""
        return Precipitation(self.value * self.unit.conversion_factor_to_millimeter)

    def to(self, target_unit: str | PrecipitationUnit) -> Precipitation:
        """Converts the pressure to the specified target unit.

        Args:
            target_unit: The unit to convert to.

        Returns:
            float: The distance value in the target unit.

        Raises:
            UnsupportedTargetUnitError: If the target unit string is not supported.
            InvalidUnitTypeError: If the target unit is
                                  neither a string nor a PressureUnit.
        """
        if isinstance(target_unit, str):
            target_unit_enum = PrecipitationUnit.from_string(target_unit)
        elif isinstance(target_unit, PrecipitationUnit):
            target_unit_enum = target_unit
        else:
            raise InvalidUnitTypeError(type(target_unit), [str, PrecipitationUnit])

        millimeter = self.to_millimeter()
        return Precipitation(
            millimeter.value / target_unit_enum.conversion_factor_to_millimeter,
            target_unit_enum,
        )

    def __str__(self) -> str:
        """Returns a pretty name."""
        return f"{self.value} {self.unit}"


class PowerPerUnitArea:
    """A class to represent amount of power per unit area with various units.

    Uses an Enum and a string for unit management.
    """

    def __init__(
        self,
        value: float,
        unit: PowerPerUnitAreaUnit = PowerPerUnitAreaUnit.WATT_PER_SQ_METER,
    ) -> None:
        """Initializes a PowerPerUnitArea object.

        Args:
            value: The value of the power per unit area.
            unit: The unit of the power per unit area.
                  Defaults to PowerPerUnitAreaUnit.WATT_PER_SQ_METER (mm).
                  Can be a PowerPerUnitAreaUnit enum member.
        """
        if not isinstance(value, (float, int)):
            InvalidPowerPerUnitAreaValueTypeError(type(value), [float, int])
        self.value = float(value)

        if isinstance(unit, PowerPerUnitAreaUnit):
            self.unit = unit
        else:
            raise InvalidUnitTypeError(type(unit), [str, PowerPerUnitArea])

    def to_watt_per_sq_meter(self) -> PowerPerUnitArea:
        """Converts the distance to watt per square meters."""
        return PowerPerUnitArea(
            self.value
            * self.unit.conversion_factor_to_watt_per_sq_meter,
        )

    def to(self, target_unit: str | PowerPerUnitAreaUnit) -> PowerPerUnitArea:
        """Converts the power per unit area to the specified target unit.

        Args:
            target_unit: The unit to convert to.

        Returns:
            float: The distance value in the target unit.

        Raises:
            UnsupportedTargetUnitError: If the target unit string is not supported.
            InvalidUnitTypeError: If the target unit is
                                  not a PowerPerUnitAreaUnit.
        """
        if not isinstance(target_unit, PowerPerUnitAreaUnit):
            raise InvalidUnitTypeError(type(target_unit), [str, PowerPerUnitAreaUnit])
        target_unit_enum = target_unit

        watt_per_sq_meter = self.to_watt_per_sq_meter()
        return PowerPerUnitArea(
            watt_per_sq_meter.value
            / target_unit_enum.conversion_factor_to_watt_per_sq_meter,
            target_unit_enum,
        )

    def __str__(self) -> str:
        """Returns a pretty name."""
        return f"{self.value} {self.unit}"
