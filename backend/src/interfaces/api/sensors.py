from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.readings.dto import ReadingDto
from src.application.readings.service import ReadingIngest
from src.application.sensors.service import SensorService
from src.domain.sensors.errors import DeviceNotFoundError, SensorReadError
from src.infrastructure.adapters.sensors.selector import select_sensor_port
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class CreateSensorRequest(BaseModel):
    type: str
    display_name: Optional[str] = None


class SensorResponse(BaseModel):
    id: UUID
    device_type: str
    display_name: str
    default_config: Dict[str, Any]
    device_family: str = "simulation"
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True


def get_ingest(db: Session = Depends(get_db)) -> ReadingIngest:
    return ReadingIngest(DeviceRepository(db), ReadingRepository(db), select_sensor_port)


@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
def create_sensor(payload: CreateSensorRequest, db: Session = Depends(get_db)):
    repo = DeviceRepository(db)
    service = SensorService(repo)
    try:
        return service.create_sensor(type_key=payload.type, display_name=payload.display_name)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("", response_model=List[SensorResponse])
def list_sensors(db: Session = Depends(get_db)):
    repo = DeviceRepository(db)
    service = SensorService(repo)
    return service.list_sensors()


@router.post("/{sensor_id}/read", response_model=ReadingDto, status_code=status.HTTP_201_CREATED)
def read_sensor(sensor_id: UUID, ingest: ReadingIngest = Depends(get_ingest)):
    """Trigger one read through the sensor's adapter, store it, return the normalized reading."""
    try:
        return ingest.take_reading(sensor_id)
    except DeviceNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except SensorReadError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("/{sensor_id}/readings", response_model=List[ReadingDto])
def list_readings(
    sensor_id: UUID,
    limit: int = Query(20, ge=1, le=500),
    ingest: ReadingIngest = Depends(get_ingest),
):
    """Most recent readings first. The UI polls this with limit=1 until Phase 12."""
    try:
        return ingest.list_readings(sensor_id, limit)
    except DeviceNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except SensorReadError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))