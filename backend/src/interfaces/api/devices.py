from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.application.devices.dto import DeviceDto
from src.application.devices.mappers import map_device_to_dto
from src.application.devices.family_service import DeviceFamilyService
from src.domain.devices.family_factory import SimulationFactory, EdgeFactory

router = APIRouter(prefix="/api/devices", tags=["devices"])

def get_device_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    """
    Dependency injection for the device family service.
    Registers the available factories (Simulation and Edge).
    """
    repo = DeviceRepository(db)
    service = DeviceFamilyService(repo)
    
    # Register concrete factories (Abstract Factory pattern)
    service.register_factory(SimulationFactory())
    service.register_factory(EdgeFactory())
    
    return service

@router.get("", response_model=List[DeviceDto])
def list_devices(
    family: Optional[str] = Query(None, description="Filter by device family (e.g., simulation, edge)"),
    role: Optional[str] = Query(None, description="Filter by device role (e.g., sensor, actuator)"),
    service: DeviceFamilyService = Depends(get_device_service)
):
    """
    List devices with optional filtering by family and role.
    """
    devices = service.list_devices(family=family, role=role)
    return [map_device_to_dto(device) for device in devices]

@router.post("/provision", response_model=List[DeviceDto], status_code=201)
def provision_family(
    family: str = Query(..., description="The family key to provision (e.g., simulation, edge)"),
    service: DeviceFamilyService = Depends(get_device_service)
):
    """
    Provision a coherent kit of sensors and actuators for a specific device family.
    """
    try:
        devices = service.provision_family(family)
        return [map_device_to_dto(device) for device in devices]
    except ValueError as e:
        # Catch domain/application errors (like an unknown family key) and map to 400
        raise HTTPException(status_code=400, detail=str(e))