from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

@dataclass(frozen=True)
class Zone:
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: Dict[str, Any] = field(default_factory=dict)
    id: Optional[UUID] = None
    location_id: Optional[UUID] = None

@dataclass(frozen=True)
class Location:
    name: str
    zones: Tuple[Zone, ...] = field(default_factory=tuple)
    id: Optional[UUID] = None

@dataclass(frozen=True)
class LocationConfig:
    location: Location