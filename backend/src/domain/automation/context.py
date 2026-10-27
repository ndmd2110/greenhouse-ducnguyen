from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class LocationAutomationContext:
    """Everything a strategy may look at for ONE zone. Plain data, no ORM rows.

    `moisture` is None when no moisture sensor is assigned to the zone (or the
    sensor has not produced a reading yet). Strategies must not guess a value.
    """

    location_id: UUID
    zone_id: UUID
    low: float
    high: float
    moisture: Optional[float] = None
    light: Optional[float] = None
    zone_name: str = ""


@dataclass(frozen=True)
class ZoneSnapshot:
    """What the repository hands the application layer for one zone."""

    zone_id: UUID
    zone_name: str
    low: float
    high: float
    moisture: Optional[float] = None
    light: Optional[float] = None