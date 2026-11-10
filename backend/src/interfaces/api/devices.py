from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.application.devices.dto import DeviceDto, TransitionRequest
from src.application.devices.family_service import DeviceFamilyService
from src.application.devices.state_service import ActuatorStateService
from src.domain.actuators.errors import IllegalTransitionError, UnknownStateError
from src.domain.devices.family_factory import SimulationFactory, EdgeFactory
from uuid import UUID
from src.application.readings.dto import SamplingDto, SamplingUpdateDto
from src.domain.sensors.errors import DeviceNotFoundError, InvalidSamplingError
from src.domain.sensors.sampling import validate_sampling_interval

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


def get_state_service(db: Session = Depends(get_db)) -> ActuatorStateService:
    return ActuatorStateService.from_session(db)


@router.get("", response_model=List[DeviceDto])
def list_devices(
    family: Optional[str] = Query(None, description="Filter by device family (e.g., simulation, edge)"),
    role: Optional[str] = Query(None, description="Filter by device role (e.g., sensor, actuator)"),
    service: DeviceFamilyService = Depends(get_device_service),
    states: ActuatorStateService = Depends(get_state_service),
):
    """
    List devices with optional filtering by family and role.
    Actuators include `state` and `allowed_commands`.
    """
    devices = service.list_devices(family=family, role=role)
    return states.to_dtos(devices)


@router.post("/provision", response_model=List[DeviceDto], status_code=201)
def provision_family(
    family: str = Query(..., description="The family key to provision (e.g., simulation, edge)"),
    service: DeviceFamilyService = Depends(get_device_service),
    states: ActuatorStateService = Depends(get_state_service),
):
    """
    Provision a coherent kit of sensors and actuators for a specific device family.
    """
    try:
        devices = service.provision_family(family)
        return states.to_dtos(devices)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{device_id}/transition", response_model=DeviceDto)
def transition_device(
    device_id: UUID,
    body: TransitionRequest,
    states: ActuatorStateService = Depends(get_state_service),
):
    """Demo endpoint: move an actuator to `target`. 404 missing actuator, 409 illegal edge, 400 unknown state."""
    try:
        return states.transition(device_id, body.target)
    except DeviceNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except IllegalTransitionError as err:
        raise HTTPException(status_code=409, detail=str(err))
    except UnknownStateError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.patch("/{device_id}/sampling", response_model=SamplingDto)
def update_sampling(
    device_id: UUID,
    body: SamplingUpdateDto,
    db: Session = Depends(get_db),
):
    """Set sampling_interval_seconds (min 5) and tracking_enabled for a device."""
    try:
        interval = validate_sampling_interval(body.sampling_interval_seconds)
        device = DeviceRepository(db).update_sampling(device_id, interval, body.tracking_enabled)
    except DeviceNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except InvalidSamplingError as err:
        raise HTTPException(status_code=400, detail=str(err))
    return SamplingDto(
        device_id=device.id,
        sampling_interval_seconds=device.sampling_interval_seconds,
        tracking_enabled=device.tracking_enabled,
    )