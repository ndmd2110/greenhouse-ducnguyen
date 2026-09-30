from typing import Any, Mapping, Optional

from src.domain.sensors.errors import InvalidSamplingError

MIN_SAMPLING_INTERVAL_SECONDS = 5
DEFAULT_SAMPLING_INTERVAL_SECONDS = 300


def validate_sampling_interval(seconds: Any) -> int:
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise InvalidSamplingError("sampling_interval_seconds must be an integer.")
    if seconds < MIN_SAMPLING_INTERVAL_SECONDS:
        raise InvalidSamplingError(
            f"sampling_interval_seconds must be at least {MIN_SAMPLING_INTERVAL_SECONDS} (got {seconds})."
        )
    return seconds


def initial_sampling_interval(
    default_config: Optional[Mapping[str, Any]],
    fallback: int = DEFAULT_SAMPLING_INTERVAL_SECONDS,
) -> int:
    """For a new device: copy the creator's interval from default_config if valid."""
    value = (default_config or {}).get("sampling_interval_seconds")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= MIN_SAMPLING_INTERVAL_SECONDS:
        return int(value)
    return fallback