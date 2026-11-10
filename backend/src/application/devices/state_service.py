from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.application.devices.dto import DeviceDto
from src.application.devices.mappers import map_device_to_dto
from src.domain.devices.entity import Device
from src.domain.sensors.errors import DeviceNotFoundError
from src.infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from src.infrastructure.persistence.device_repository import DeviceRepository


class ActuatorStateService:
    """Loads, transitions and saves actuator state. Transition rules live in the domain."""

    def __init__(self, devices: DeviceRepository, states: ActuatorStateRepository) -> None:
        self._devices = devices
        self._states = states

    @classmethod
    def from_session(cls, session: Session) -> "ActuatorStateService":
        return cls(DeviceRepository(session), ActuatorStateRepository(session))

    def to_dtos(self, devices: list[Device]) -> list[DeviceDto]:
        """Device read models with state + allowed_commands filled in for actuators."""
        actuator_ids = [d.id for d in devices if d.role == "actuator"]
        contexts = self._states.get_many(actuator_ids)
        return [map_device_to_dto(d, contexts.get(d.id)) for d in devices]

    def transition(self, device_id: UUID, target: str) -> DeviceDto:
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(f"Actuator '{device_id}' was not found.")
        context = self._states.get_or_create(device_id)
        context.transition(target)  # raises before anything is saved when the edge is illegal
        self._states.save(context)
        return map_device_to_dto(device, context)