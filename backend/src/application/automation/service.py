from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.application.automation.dto import (
    AutomationRuleDto,
    RecommendationDto,
    StrategyInfoDto,
    ZoneRecommendationDto,
)
from src.domain.automation.context import LocationAutomationContext
from src.domain.automation.errors import LocationNotFoundError
from src.domain.automation.strategy import (
    ACTION_IRRIGATE,
    ACTION_WAIT,
    DEFAULT_STRATEGY_KEY,
    available_strategies,
    get_strategy,
)
from src.infrastructure.persistence.automation_repository import AutomationRepository


class AutomationService:
    def __init__(self, repository: AutomationRepository) -> None:
        self._repo = repository

    def list_strategies(self) -> list[StrategyInfoDto]:
        return [StrategyInfoDto(key=s.key, description=s.description) for s in available_strategies()]

    def get_rule(self, location_id: UUID) -> AutomationRuleDto:
        self._require_location(location_id)
        key = self._repo.get_strategy_key(location_id)
        return AutomationRuleDto(location_id=location_id, strategy_key=key or DEFAULT_STRATEGY_KEY, is_default=key is None)

    def set_strategy(self, location_id: UUID, strategy_key: str) -> AutomationRuleDto:
        self._require_location(location_id)
        get_strategy(strategy_key)  # unknown key -> UnknownStrategyError, nothing persisted
        self._repo.upsert_strategy_key(location_id, strategy_key)
        return AutomationRuleDto(location_id=location_id, strategy_key=strategy_key)

    def evaluate(self, location_id: UUID, strategy_key: Optional[str] = None) -> RecommendationDto:
        # 1. location or 404
        self._require_location(location_id)
        # 2. persisted key (an explicit override is an optional extra)
        key = strategy_key or self._repo.get_strategy_key(location_id) or DEFAULT_STRATEGY_KEY
        strategy = get_strategy(key)  # rejects unknown keys before any decide()
        # 3-4. latest readings + this location's zone thresholds, as plain snapshots
        snapshots = self._repo.list_zone_snapshots(location_id)
        if not snapshots:
            return RecommendationDto(
                location_id=location_id, strategy_key=key, action=ACTION_WAIT, reason="Location has no zones to evaluate", zones=[]
            )
        # 5-6. one context per zone, one decide() per context
        zones: list[ZoneRecommendationDto] = []
        for snap in snapshots:
            context = LocationAutomationContext(
                location_id=location_id,
                zone_id=snap.zone_id,
                zone_name=snap.zone_name,
                low=snap.low,
                high=snap.high,
                moisture=snap.moisture,
                light=snap.light,
            )
            rec = strategy.decide(context)
            zones.append(
                ZoneRecommendationDto(
                    zone_id=snap.zone_id,
                    zone_name=snap.zone_name,
                    action=rec.action,
                    reason=rec.reason,
                    score=rec.score,
                    moisture=snap.moisture,
                )
            )
        return RecommendationDto(
            location_id=location_id,
            strategy_key=key,
            action=ACTION_IRRIGATE if any(z.action == ACTION_IRRIGATE for z in zones) else ACTION_WAIT,
            reason=zones[0].reason if len(zones) == 1 else "; ".join(f"{z.zone_name}: {z.reason}" for z in zones),
            zones=zones,
        )

    def _require_location(self, location_id: UUID) -> None:
        if not self._repo.location_exists(location_id):
            raise LocationNotFoundError(f"Location '{location_id}' was not found.")