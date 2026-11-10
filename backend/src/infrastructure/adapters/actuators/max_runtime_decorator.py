from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from src.domain.actuators.errors import PolicyViolationError
from src.domain.actuators.ports import ActuatorPort
from src.domain.actuators.state import RUNNING
from src.infrastructure.persistence.actuator_state_repository import ActuatorStateRepository

MAX_RUN_TIME = timedelta(minutes=30)
POLICY_NAME = "maxRunTime"
BLOCK_MESSAGE = "Max run time exceeded"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MaxRunTimeActuatorDecorator(ActuatorPort):
    """Blocks apply() once the actuator has been `running` for at least 30 minutes.

    The clock starts at actuator_states.updated_at. The command string is not inspected here.
    """

    def __init__(
        self,
        inner: ActuatorPort,
        states: ActuatorStateRepository,
        clock: Callable[[], datetime] = _utcnow,
        max_run_time: timedelta = MAX_RUN_TIME,
    ) -> None:
        self._inner = inner
        self._states = states
        self._clock = clock
        self._max_run_time = max_run_time

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        context = self._states.get(device_id)
        if (
            context is not None
            and context.state == RUNNING
            and self._clock() - context.updated_at >= self._max_run_time
        ):
            raise PolicyViolationError(POLICY_NAME, BLOCK_MESSAGE)  # inner is never reached
        self._inner.apply(device_id, command, payload)