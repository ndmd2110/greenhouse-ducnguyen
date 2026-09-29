from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass(frozen=True)
class Device:
    id: Optional[UUID]
    device_type: str
    role: str
    device_family: str
    display_name: str
    default_config: dict
    zone_id: Optional[UUID] = None
    location_id: Optional[UUID] = None