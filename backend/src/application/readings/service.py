from typing import Callable
from uuid import UUID

from src.application.readings.dto import ReadingDto, reading_to_dto
from src.domain.devices.entity import Device
from src.domain.sensors.errors import DeviceNotFoundError, SensorReadError
from src.domain.sensors.ports import SensorPort
from src.domain.sensors.reading import Reading
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

PortSelector = Callable[[Device], SensorPort]


class ReadingIngest:
    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        select_port: PortSelector,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._select_port = select_port

    def _require_sensor(self, device_id: UUID) -> Device:
        device = self._devices.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device '{device_id}' was not found.")
        if device.role != "sensor":
            raise SensorReadError(f"Device '{device_id}' is not a sensor.")
        return device

    def take_reading(self, device_id: UUID) -> ReadingDto:
        """One-shot read: pick adapter -> port.read() -> persist -> DTO."""
        device = self._require_sensor(device_id)
        reading = self._select_port(device).read(device)
        return self._persist(reading)

    def record(self, device_id: UUID, reading: Reading) -> ReadingDto:
        """Persist an already translated reading (sampler now, MQTT in Phase 12)."""
        self._require_sensor(device_id)
        if reading.device_id != device_id:
            raise SensorReadError("Reading device_id does not match the target device.")
        return self._persist(reading)

    def list_readings(self, device_id: UUID, limit: int = 20) -> list[ReadingDto]:
        self._require_sensor(device_id)
        return [reading_to_dto(r) for r in self._readings.list_for_device(device_id, limit)]

    def _persist(self, reading: Reading) -> ReadingDto:
        # Phase 11 will publish `reading.created` here, only when tracking is on.
        return reading_to_dto(self._readings.insert(reading))