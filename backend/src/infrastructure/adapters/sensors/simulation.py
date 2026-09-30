import random
from datetime import datetime
from typing import Callable, Optional

from src.domain.devices.entity import Device
from src.domain.sensors.errors import SensorReadError
from src.domain.sensors.ports import SensorPort
from src.domain.sensors.reading import SOURCE_SIMULATION, Reading
from src.infrastructure.adapters.sensors.profiles import PROFILES, utc_now


class SimulationSensorAdapter(SensorPort):
    """Generates a plausible value in code. Mocked driver, no hardware."""

    def __init__(self, rng: Optional[random.Random] = None, clock: Optional[Callable[[], datetime]] = None) -> None:
        self._rng = rng or random.Random()
        self._clock = clock or utc_now

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorReadError("Cannot read an unpersisted device.")
        profile = PROFILES.get(device.device_type)
        if profile is None:
            raise SensorReadError(f"No simulation profile for device type '{device.device_type}'.")
        value = round(self._rng.uniform(profile.low, profile.high), profile.digits)
        return Reading(
            device_id=device.id, value=value, unit=profile.unit,
            source=SOURCE_SIMULATION, recorded_at=self._clock(),
        )