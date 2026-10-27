from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.application.overview.dto import LocationOverviewDto
from src.application.overview.facade import LocationOverviewFacade
from src.domain.automation.errors import LocationNotFoundError
from src.infrastructure.persistence.base import get_db

router = APIRouter(prefix="/api", tags=["overview"])


def get_overview_facade(db: Session = Depends(get_db)) -> LocationOverviewFacade:
    return LocationOverviewFacade.from_session(db)


@router.get("/locations/{location_id}/overview", response_model=LocationOverviewDto)
def get_location_overview(location_id: UUID, facade: LocationOverviewFacade = Depends(get_overview_facade)):
    """One snapshot: assigned device counts, zones (devices + latest readings), strategy, recommendation."""
    try:
        return facade.get_overview(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc