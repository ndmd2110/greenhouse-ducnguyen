from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

SOURCE_SIMULATION = "simulation"
SOURCE_MQTT = "mqtt"
SOURCE_VENDOR = "vendor"


@dataclass(frozen=True)
class Reading:
    device_id: UUID
    value: float
    unit: str
    source: str  # "simulation" | "mqtt" | "vendor"
    recorded_at: datetime  # timezone-aware

    def __post_init__(self) -> None:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("Reading.recorded_at must be timezone-aware.")