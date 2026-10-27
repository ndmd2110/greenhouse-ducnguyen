from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class StrategySaveRequest(BaseModel):
    strategy_key: str


class StrategyInfoDto(BaseModel):
    key: str
    description: str


class AutomationRuleDto(BaseModel):
    location_id: UUID
    strategy_key: str
    is_default: bool = False  # True when nothing is persisted yet and the default applies


class ZoneRecommendationDto(BaseModel):
    zone_id: UUID
    zone_name: str
    action: str
    reason: str
    score: Optional[float] = None
    moisture: Optional[float] = None


class RecommendationDto(BaseModel):
    location_id: UUID
    strategy_key: str
    action: str  # "irrigate" if any zone needs water, else "wait"
    reason: str
    zones: List[ZoneRecommendationDto]