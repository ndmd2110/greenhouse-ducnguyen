import random
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, Protocol

from src.domain.devices.entity import Device
from src.domain.sensors.errors import SensorReadError
from src.domain.sensors.ports import SensorPort
from src.domain.sensors.reading import SOURCE_VENDOR, Reading
from src.infrastructure.adapters.sensors.profiles import PROFILES, utc_now

# The "vendor" speaks integers + a scale, upper-case unit codes and epoch milliseconds.
_UNIT_CODES = {"VWC": "vwc", "LUX": "lux"}
_VENDOR_UNIT_CODE = {"vwc": "VWC", "lux": "LUX"}
_VENDOR_SCALE = {"vwc": 1000, "lux": 10}


class VendorClient(Protocol):
    def fetch(self, device: Device) -> Mapping[str, Any]: ...


class FakeVendorClient:
    """Stands in for a vendor SDK. Returns the vendor's raw shape, not ours."""

    def __init__(self, rng: Optional[random.Random] = None, clock: Optional[Callable[[], datetime]] = None) -> None:
        self._rng = rng or random.Random()
        self._clock = clock or utc_now

    def fetch(self, device: Device) -> Mapping[str, Any]:
        profile = PROFILES.get(device.device_type)
        if profile is None:
            raise SensorReadError(f"Vendor stub does not support device type '{device.device_type}'.")
        scale = _VENDOR_SCALE[profile.unit]
        value = self._rng.uniform(profile.low, profile.high)
        return {
            "measurement": {"raw": int(round(value * scale)), "scale": scale, "unit_code": _VENDOR_UNIT_CODE[profile.unit]},
            "ts_epoch_ms": int(self._clock().timestamp() * 1000),
        }


class VendorStubSensorAdapter(SensorPort):
    """Translates the vendor's raw payload into a normalized Reading (source='vendor')."""

    def __init__(self, client: Optional[VendorClient] = None) -> None:
        self._client = client or FakeVendorClient()

    def read(self, device: Device) -> Reading:
        return self.translate(device, self._client.fetch(device))

    def translate(self, device: Device, raw: Mapping[str, Any]) -> Reading:
        if device.id is None:
            raise SensorReadError("Cannot translate a reading for an unpersisted device.")
        try:
            measurement = raw["measurement"]
            raw_value = measurement["raw"]
            scale = measurement["scale"]
            unit_code = measurement["unit_code"]
            ts_ms = raw["ts_epoch_ms"]
        except (KeyError, TypeError) as exc:
            raise SensorReadError(f"Malformed vendor payload: missing {exc}.") from exc

        numbers = (raw_value, scale, ts_ms)
        if any(isinstance(n, bool) or not isinstance(n, (int, float)) for n in numbers) or scale == 0:
            raise SensorReadError("Malformed vendor payload: raw, scale and ts_epoch_ms must be numbers (scale != 0).")
        unit = _UNIT_CODES.get(unit_code)
        if unit is None:
            raise SensorReadError(f"Unknown vendor unit code '{unit_code}'.")

        return Reading(
            device_id=device.id,
            value=raw_value / scale,
            unit=unit,
            source=SOURCE_VENDOR,
            recorded_at=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
        )