from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.actuators.dto import ExecutionDto
from src.domain.actuators.errors import PolicyViolationError
from src.domain.actuators.execution import ExecutionRecord
from src.domain.actuators.ports import ActuatorPort
from src.domain.sensors.errors import DeviceNotFoundError
from src.infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from src.infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from src.infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from src.infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.execution_log_repository import ExecutionLogRepository


def _to_dto(record: ExecutionRecord) -> ExecutionDto:
    return ExecutionDto(
        id=record.id,
        device_id=record.device_id,
        success=record.success,
        policy_applied=record.policy_applied,
        message=record.message,
        created_at=record.created_at,
    )


class ActuatorExecutionService:
    """Composition root for the decorator chain: Logging -> MaxRunTime -> SimulationActuatorAdapter."""

    def __init__(
        self,
        devices: DeviceRepository,
        logs: ExecutionLogRepository,
        states: ActuatorStateRepository,
        inner: Optional[ActuatorPort] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._devices = devices
        self._logs = logs
        max_runtime_kwargs = {"clock": clock} if clock is not None else {}
        self._logging = LoggingActuatorDecorator(
            MaxRunTimeActuatorDecorator(inner or SimulationActuatorAdapter(), states, **max_runtime_kwargs),
            logs,
        )

    @classmethod
    def from_session(cls, session: Session) -> "ActuatorExecutionService":
        return cls(DeviceRepository(session), ExecutionLogRepository(session), ActuatorStateRepository(session))

    @property
    def port(self) -> ActuatorPort:
        """The decorated port. Callers (and Phase 10) only see ActuatorPort."""
        return self._logging

    def apply(self, device_id: UUID, command: str, payload: dict) -> ExecutionDto:
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(f"Actuator '{device_id}' was not found.")
        try:
            self._logging.apply(device_id, command, payload)
        except PolicyViolationError:
            pass  # already written to actuator_execution_log as success=false
        assert self._logging.last_entry is not None
        return _to_dto(self._logging.last_entry)

    def list_recent(self, limit: int = 20) -> list[ExecutionDto]:
        return [_to_dto(r) for r in self._logs.list_recent(limit)]