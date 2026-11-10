from pydantic import BaseModel, Field
from uuid import UUID
from typing import Dict, Any, List, Literal


class DeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: Literal["sensor", "actuator"]
    device_family: str
    display_name: str
    default_config: Dict[str, Any]
    zone_id: UUID | None = None
    location_id: UUID | None = None
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True
    # Phase 8: only actuators carry a lifecycle state; sensors get null / [].
    state: str | None = None
    allowed_commands: List[str] = Field(default_factory=list)


class TransitionRequest(BaseModel):
    target: str