class WolframAPIError(Exception):
    """Custom exception for Wolfram Alpha API errors."""


class WolframRateLimitError(WolframAPIError):
    """Custom exception for rate limiting errors."""


class WolframQueryError(WolframAPIError):
    """Custom exception for query-specific errors (e.g., invalid appid, bad query)."""


class WolframParseError(WolframAPIError):
    """Custom exception for XML parsing errors."""
