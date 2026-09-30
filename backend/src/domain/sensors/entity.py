from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import UUID

@dataclass
class Sensor:
    device_type: str
    display_name: str
    default_config: Dict[str, Any] = field(default_factory=dict)
    id: Optional[UUID] = None
    device_family: str = "simulation"
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True