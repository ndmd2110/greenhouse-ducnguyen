from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from src.domain.actuators.errors import IllegalTransitionError
from src.domain.actuators.state import INITIAL_STATE, StateSpec, get_spec


class ActuatorContext:
    """Current lifecycle state of one actuator. Guards every transition."""

    def __init__(self, device_id: UUID, state: str = INITIAL_STATE, updated_at: Optional[datetime] = None) -> None:
        self.device_id = device_id
        self._spec: StateSpec = get_spec(state)
        self.updated_at: datetime = updated_at or datetime.now(timezone.utc)

    @property
    def state(self) -> str:
        return self._spec.name

    def transition(self, target: str, *, now: Optional[datetime] = None) -> None:
        """Move to `target` or raise. Nothing is mutated when it raises."""
        target_spec = get_spec(target)  # unknown state -> UnknownStateError
        if target not in self._spec.next_states:
            allowed = ", ".join(sorted(self._spec.next_states)) or "none"
            raise IllegalTransitionError(
                f"Cannot change state from '{self.state}' to '{target}'. Allowed from '{self.state}': {allowed}."
            )
        self._spec = target_spec
        self.updated_at = now or datetime.now(timezone.utc)

    def allowed_commands(self) -> list[str]:
        return list(self._spec.commands)

    def allowed_targets(self) -> list[str]:
        return sorted(self._spec.next_states)