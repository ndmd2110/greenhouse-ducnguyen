import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppliedCommand:
    device_id: UUID
    command: str
    payload: dict[str, Any]
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SimulationActuatorAdapter(ActuatorPort):
    """Records intent in memory and logs it. No GPIO. Phase 9 wraps this with decorators."""

    def __init__(self) -> None:
        self._applied: list[AppliedCommand] = []

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        self._applied.append(AppliedCommand(device_id=device_id, command=command, payload=dict(payload)))
        logger.info("Simulated actuator %s: %s %s", device_id, command, payload)

    @property
    def applied(self) -> list[AppliedCommand]:
        return list(self._applied)