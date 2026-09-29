from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ZoneCreateRequest(BaseModel):
    name: str
    moisture_threshold_low: float = Field(..., ge=0.0, le=1.0)
    moisture_threshold_high: float = Field(..., ge=0.0, le=1.0)
    schedule: Dict[str, Any] = Field(default_factory=dict)


class ZoneUpdateRequest(ZoneCreateRequest):
    pass


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: Dict[str, Any] = Field(default_factory=dict)


class LocationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class LocationConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location: LocationSummaryResponse
    zones: List[ZoneResponse]


class LocationCreateRequest(BaseModel):
    location_name: str
    zones: List[ZoneCreateRequest]


class DeviceZoneAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: UUID | None = None
