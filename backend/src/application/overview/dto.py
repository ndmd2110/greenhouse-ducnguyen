from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LocationSummaryDto(BaseModel):
    id: UUID
    name: str


class DeviceCountsDto(BaseModel):
    sensor: int = 0
    actuator: int = 0


class OverviewDeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: str
    display_name: Optional[str] = None


class OverviewReadingDto(BaseModel):
    device_id: UUID
    value: float
    unit: str
    recorded_at: datetime
    tracking_enabled: bool  # copied from the device
    sampling_interval_seconds: int  # copied from the device


class OverviewZoneDto(BaseModel):
    id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    devices: List[OverviewDeviceDto] = Field(default_factory=list)
    latest_readings: List[OverviewReadingDto] = Field(default_factory=list)


class OverviewRecommendationDto(BaseModel):
    action: str
    reason: str


class LocationOverviewDto(BaseModel):
    location: LocationSummaryDto
    device_counts: DeviceCountsDto
    zones: List[OverviewZoneDto]
    strategy_key: Optional[str] = None
    last_recommendation: Optional[OverviewRecommendationDto] = None