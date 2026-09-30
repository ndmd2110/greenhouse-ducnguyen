from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.sensors.reading import Reading


class ReadingDto(BaseModel):
    device_id: UUID
    value: float
    unit: str
    source: str
    recorded_at: datetime


class SamplingUpdateDto(BaseModel):
    """PATCH /api/devices/{id}/sampling body (used in step 5)."""
    sampling_interval_seconds: int
    tracking_enabled: bool


class SamplingDto(BaseModel):
    device_id: UUID
    sampling_interval_seconds: int
    tracking_enabled: bool


def reading_to_dto(reading: Reading) -> ReadingDto:
    return ReadingDto(
        device_id=reading.device_id,
        value=reading.value,
        unit=reading.unit,
        source=reading.source,
        recorded_at=reading.recorded_at,
    )