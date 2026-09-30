from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SensorProfile:
    low: float
    high: float
    unit: str
    digits: int


PROFILES: dict[str, SensorProfile] = {
    "moisture_sensor": SensorProfile(low=0.2, high=0.6, unit="vwc", digits=3),
    "light_sensor": SensorProfile(low=200.0, high=2000.0, unit="lux", digits=1),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)