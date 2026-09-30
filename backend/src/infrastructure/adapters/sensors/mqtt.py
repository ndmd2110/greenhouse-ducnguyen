from datetime import datetime
from typing import Any, Callable, Mapping, Optional

from src.domain.devices.entity import Device
from src.domain.sensors.errors import SensorReadError
from src.domain.sensors.ports import SensorPort
from src.domain.sensors.reading import SOURCE_MQTT, Reading
from src.infrastructure.adapters.sensors.profiles import utc_now


class MqttSensorAdapter(SensorPort):
    """Translates an inbound payload dict like {"value": 0.41, "unit": "vwc"}. Never opens a socket."""

    def __init__(self, clock: Optional[Callable[[], datetime]] = None) -> None:
        self._clock = clock or utc_now

    def translate(self, device: Device, payload: Mapping[str, Any]) -> Reading:
        if device.id is None:
            raise SensorReadError("Cannot translate a reading for an unpersisted device.")
        try:
            value = payload["value"]
            unit = payload["unit"]
        except (KeyError, TypeError) as exc:
            raise SensorReadError(f"Malformed MQTT payload: missing {exc}.") from exc
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SensorReadError("Malformed MQTT payload: 'value' must be a number.")
        if not isinstance(unit, str) or not unit.strip():
            raise SensorReadError("Malformed MQTT payload: 'unit' must be a non-empty string.")
        return Reading(
            device_id=device.id, value=float(value), unit=unit.strip(),
            source=SOURCE_MQTT, recorded_at=self._clock(),
        )

    def read(self, device: Device) -> Reading:
        # MQTT devices push their readings; there is nothing to pull.
        raise SensorReadError(
            "MQTT sensors push their readings; a manual read is not possible. "
            "Ingest arrives with device HTTP or the optional broker in Phase 12."
        )