from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


class InvalidTypeError(TypeError):
    """Custom exception raised when the input type of anything is invalid."""
    def __init__(
            self,
            actual_type: object,
            expected_types: Iterable[object],
            message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        self.actual_type = actual_type
        self.expected_types = expected_types

        expected_type_names = [
            t.__name__ if hasattr(t, "__name__") else str(t) for t in expected_types
        ]
        formatted_expected_types = ", ".join(expected_type_names)

        if message is None:
            message = (
                f"Expected type "
                f"'{formatted_expected_types}' "
                f"but got '{actual_type.__name__}'"
            )
        super().__init__(message)


class InvalidDirectionTypeError(InvalidTypeError):
    """Custom exception raised when the input type for Direction is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidUVTypeError(InvalidTypeError):
    """Custom exception raised when the input type for UltravioletIndex is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidWeatherKindTypeError(InvalidTypeError):
    """Custom exception raised when the input type for WeatherKind is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidUnitTypeError(InvalidTypeError):
    """Custom exception raised when the unit type is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidSpeedTypeError(InvalidTypeError):
    """Custom exception raised when the value type for Speed is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidPressureValueTypeError(InvalidTypeError):
    """Custom exception raised when the value type for Pressure is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidPrecipitationValueTypeError(InvalidTypeError):
    """Custom exception raised when the value type for Precipitation is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidPowerPerUnitAreaValueTypeError(InvalidTypeError):
    """Custom exception raised when the value type for PowerPerUnitArea is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidWindDirectionTypeError(InvalidTypeError):
    """Custom exception raised when the direction type for Wind is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidWindSpeedTypeError(InvalidTypeError):
    """Custom exception raised when the speed type for Wind is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidTemperatureValueTypeError(InvalidTypeError):
    """Custom exception raised when the speed type for Wind is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidDistanceValueTypeError(InvalidTypeError):
    """Custom exception raised when the distance type for Distance is invalid."""
    def __init__(
        self,
        actual_type: object,
        expected_types: Iterable[object],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid input type.

        Args:
            actual_type: The actual type inputted.
            expected_types: The expected types expected by a function.
            message: A custom message shown. Optional.
        """
        super().__init__(actual_type, expected_types, message)


class InvalidWeatherKindIDError(ValueError):
    """Custom exception raised when the ID for WeatherKind is invalid."""
    def __init__(
        self,
        actual_id: int,
        expected_id: Iterable[int],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid ID for WeatherKind.

        Args:
            actual_id: The actual invalid ID.
            expected_id: The expected list of ID.
            message: A custom message.
        """
        msg = (
            f"{actual_id} is not found in the list of weather codes. "
            f"Those includes {', '.join(map(str, expected_id))}."
        ) if message is None else message
        super().__init__(msg)


class UnsupportedTargetUnitError(ValueError):
    """Custom exception raised when the target unit is invalid."""

    def __init__(
        self,
        actual_target_unit: str,
        expected_target_units: Iterable[str],
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid target unit.

        Args:
            actual_target_unit: The actual invalid unit.
            expected_target_units: The expected list units.
            message: A custom message.
        """
        msg = (
            f"Unsupported unit string {actual_target_unit}. "
            f"Supported units are {', '.join(map(str, expected_target_units))}."
        ) if message is None else message

        super().__init__(msg)


class InvalidTimeError(ValueError):
    """Custom exception raised when the time parsed is invalid.

    For example, if the time is '2500' or a 'text'
    """

    def __init__(
        self,
        time: str,
        message: str | None = None,
    ) -> None:
        """Initializes the object to show an invalid target unit.

        Args:
            time: The time string.
            message: A custom message.
        """
        msg = (
            f"Invalid time {time}."
            f"Make sure the string consists of only numbers"
            f"and formatting like this:\n"
            f"0 (for midnight), 300 (for 3 AM), and so on "
            f"until 2100 (for 9 PM)."
        ) if message is None else message

        super().__init__(msg)

class WeatherAPIError(Exception):
    """A base exception class for API errors."""
