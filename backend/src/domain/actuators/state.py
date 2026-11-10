from __future__ import annotations

from dataclasses import dataclass

from src.domain.actuators.errors import UnknownStateError

OFF = "off"
IDLE = "idle"
RUNNING = "running"
ERROR = "error"
MAINTENANCE = "maintenance"

INITIAL_STATE = IDLE


@dataclass(frozen=True)
class StateSpec:
    """One state: where it may go next and which commands are legal while in it."""

    name: str
    next_states: frozenset[str]
    commands: tuple[str, ...]


# The transition table. Every edge not listed here is illegal.
# "* -> error" is encoded by listing ERROR in every state except error itself.
STATES: dict[str, StateSpec] = {
    OFF: StateSpec(OFF, frozenset({IDLE, ERROR}), ()),
    IDLE: StateSpec(IDLE, frozenset({RUNNING, OFF, MAINTENANCE, ERROR}), ("start_pump",)),
    RUNNING: StateSpec(RUNNING, frozenset({IDLE, ERROR}), ("stop_pump",)),
    ERROR: StateSpec(ERROR, frozenset({IDLE, MAINTENANCE}), ()),  # error -> idle is the "reset"
    MAINTENANCE: StateSpec(MAINTENANCE, frozenset({IDLE, ERROR}), ()),
}


def get_spec(state: str) -> StateSpec:
    spec = STATES.get(state)
    if spec is None:
        raise UnknownStateError(f"Unknown actuator state '{state}'. Known: {', '.join(STATES)}.")
    return spec