from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.application.actuators.dto import ApplyRequest, ExecutionDto
from src.application.actuators.service import ActuatorExecutionService
from src.domain.sensors.errors import DeviceNotFoundError
from src.infrastructure.persistence.base import get_db

router = APIRouter(prefix="/api/actuators", tags=["actuators"])


def get_execution_service(db: Session = Depends(get_db)) -> ActuatorExecutionService:
    return ActuatorExecutionService.from_session(db)


@router.get("/executions", response_model=List[ExecutionDto])
def list_executions(
    limit: int = Query(20, ge=1, le=200),
    service: ActuatorExecutionService = Depends(get_execution_service),
):
    """Most recent actuator apply attempts (newest first), read from actuator_execution_log."""
    return service.list_recent(limit)


@router.post("/{device_id}/apply", response_model=ExecutionDto)
def apply_command(
    device_id: UUID,
    body: ApplyRequest,
    service: ActuatorExecutionService = Depends(get_execution_service),
):
    """Demo until Phase 10. Goes through Logging -> MaxRunTime -> Simulation.
    A blocked attempt still returns 200 with success=false and the policy names."""
    try:
        return service.apply(device_id, body.command, body.payload)
    except DeviceNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))