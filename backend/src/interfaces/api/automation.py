from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.application.automation.dto import AutomationRuleDto, RecommendationDto, StrategyInfoDto, StrategySaveRequest
from src.application.automation.service import AutomationService
from src.domain.automation.errors import LocationNotFoundError, UnknownStrategyError
from src.infrastructure.persistence.automation_repository import AutomationRepository
from src.infrastructure.persistence.base import get_db

router = APIRouter(prefix="/api", tags=["automation"])


def get_automation_service(db: Session = Depends(get_db)) -> AutomationService:
    return AutomationService(AutomationRepository(db))


@router.get("/automation/strategies", response_model=List[StrategyInfoDto])
def list_strategies(service: AutomationService = Depends(get_automation_service)):
    """Known strategy keys (what the dashboard dropdown shows)."""
    return service.list_strategies()


@router.get("/locations/{location_id}/automation", response_model=AutomationRuleDto)
def get_automation(location_id: UUID, service: AutomationService = Depends(get_automation_service)):
    try:
        return service.get_rule(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/locations/{location_id}/automation", response_model=AutomationRuleDto)
def set_automation(location_id: UUID, body: StrategySaveRequest, service: AutomationService = Depends(get_automation_service)):
    """Upsert the active strategy for a location."""
    try:
        return service.set_strategy(location_id, body.strategy_key)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownStrategyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/locations/{location_id}/automation/evaluate", response_model=RecommendationDto)
def evaluate_automation(
    location_id: UUID,
    strategy_key: Optional[str] = Query(None, description="Optional override; defaults to the persisted key"),
    service: AutomationService = Depends(get_automation_service),
):
    """Evaluate each zone with the location's persisted strategy and its latest moisture reading."""
    try:
        return service.evaluate(location_id, strategy_key)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownStrategyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc