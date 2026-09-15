from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from infrastructure.persistence.base import get_db
from infrastructure.persistence.device_repository import DeviceRepository
from application.sensors.service import SensorService

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

class CreateSensorRequest(BaseModel):
    type: str
    display_name: Optional[str] = None

class SensorResponse(BaseModel):
    id: UUID
    device_type: str
    display_name: str
    default_config: Dict[str, Any]

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