from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.domain.actuators.errors import PolicyViolationError
from src.domain.actuators.execution import ExecutionRecord
from src.domain.actuators.ports import ActuatorPort
from src.infrastructure.persistence.execution_log_repository import ExecutionLogRepository

LOGGING_POLICY = "logging"


class LoggingActuatorDecorator(ActuatorPort):
    """Outermost wrapper: every attempt writes one actuator_execution_log row."""

    def __init__(self, inner: ActuatorPort, log_repo: ExecutionLogRepository) -> None:
        self._inner = inner
        self._log = log_repo
        self.last_entry: Optional[ExecutionRecord] = None

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        try:
            self._inner.apply(device_id, command, payload)
        except PolicyViolationError as exc:
            self.last_entry = self._log.add(
                device_id,
                success=False,
                policy_applied=[exc.policy, LOGGING_POLICY],
                message=exc.message,
            )
            raise
        except Exception as exc:
            self.last_entry = self._log.add(
                device_id,
                success=False,
                policy_applied=[LOGGING_POLICY],
                message=str(exc),
            )
            raise
        self.last_entry = self._log.add(
            device_id,
            success=True,
            policy_applied=[LOGGING_POLICY],
            message=None,
        )