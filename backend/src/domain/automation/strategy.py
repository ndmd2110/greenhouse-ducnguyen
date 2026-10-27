from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.domain.automation.context import LocationAutomationContext
from src.domain.automation.errors import UnknownStrategyError

ACTION_IRRIGATE = "irrigate"
ACTION_WAIT = "wait"

DEFAULT_STRATEGY_KEY = "conservative"

# Aggressive strategy waters while moisture sits in the bottom 75% of the
# [low, high] band. Conservative only waters below `low`.
AGGRESSIVE_TRIGGER_FRACTION = 0.75


@dataclass(frozen=True)
class Recommendation:
    action: str  # "irrigate" | "wait"
    reason: str
    score: Optional[float] = None  # 0..1 urgency, optional


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def _no_sensor() -> Recommendation:
    return Recommendation(action=ACTION_WAIT, reason="No moisture reading available for this zone (no moisture sensor assigned)")


def _dryness(moisture: float, reference: float) -> float:
    """0 when moisture >= reference, up to 1 when the soil is bone dry."""
    if reference <= 0:
        return 0.0
    return round(max(0.0, min(1.0, (reference - moisture) / reference)), 3)


class AutomationStrategy(ABC):
    """Strategy interface: same context in, a Recommendation out."""

    key: str
    description: str

    @abstractmethod
    def decide(self, context: LocationAutomationContext) -> Recommendation: ...


class ConservativeMoistureStrategy(AutomationStrategy):
    key = "conservative"
    description = "Irrigate only when moisture drops below the zone's low threshold."

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        moisture = context.moisture
        if moisture is None:
            return _no_sensor()
        low, high = context.low, context.high
        if moisture < low:
            return Recommendation(
                ACTION_IRRIGATE,
                f"Moisture {_fmt(moisture)} is below the low threshold {_fmt(low)}",
                score=_dryness(moisture, low),
            )
        if moisture <= high:
            return Recommendation(ACTION_WAIT, f"Moisture {_fmt(moisture)} is within {_fmt(low)}\u2013{_fmt(high)}", score=0.0)
        return Recommendation(ACTION_WAIT, f"Moisture {_fmt(moisture)} is above the high threshold {_fmt(high)}", score=0.0)


class AggressiveMoistureStrategy(AutomationStrategy):
    key = "aggressive"
    description = "Irrigate early: keep moisture in the top quarter of the zone's band."

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        moisture = context.moisture
        if moisture is None:
            return _no_sensor()
        low, high = context.low, context.high
        trigger = low + AGGRESSIVE_TRIGGER_FRACTION * (high - low)
        if moisture < trigger:
            return Recommendation(
                ACTION_IRRIGATE,
                f"Moisture {_fmt(moisture)} is below the aggressive trigger {_fmt(trigger)} (band {_fmt(low)}\u2013{_fmt(high)})",
                score=_dryness(moisture, trigger),
            )
        return Recommendation(ACTION_WAIT, f"Moisture {_fmt(moisture)} is at or above the aggressive trigger {_fmt(trigger)}", score=0.0)


_REGISTRY: dict[str, type[AutomationStrategy]] = {
    cls.key: cls for cls in (ConservativeMoistureStrategy, AggressiveMoistureStrategy)
}


def available_strategies() -> list[AutomationStrategy]:
    return [cls() for cls in _REGISTRY.values()]


def get_strategy(key: str) -> AutomationStrategy:
    """Unknown key raises before any decide() call."""
    cls = _REGISTRY.get(key)
    if cls is None:
        raise UnknownStrategyError(f"Unknown strategy '{key}'. Valid keys: {sorted(_REGISTRY)}")
    return cls()