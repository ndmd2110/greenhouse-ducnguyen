import logging
from dataclasses import replace
from datetime import datetime

from src.application.readings.service import PortSelector, ReadingIngest
from src.domain.sensors.errors import SensorReadError
from src.domain.sensors.protocols import PROTOCOL_SIMULATION, resolve_protocol
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

logger = logging.getLogger(__name__)


class SimulationSampler:
    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        ingest: ReadingIngest,
        select_port: PortSelector,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._ingest = ingest
        self._select_port = select_port

    def run_once(self, now: datetime) -> int:
        """Record a reading for every due simulation sensor. Returns how many were inserted."""
        inserted = 0
        for device in self._devices.list_tracked_sensors():  # tracking_enabled already filtered
            if resolve_protocol(device) != PROTOCOL_SIMULATION:
                continue  # MQTT devices push their own readings
            last = self._readings.latest_recorded_at(device.id)
            if last is not None and (now - last).total_seconds() < device.sampling_interval_seconds:
                continue
            try:
                reading = self._select_port(device).read(device)
                # Stamp with the tick's clock so the interval logic (and fake-clock tests) is consistent.
                self._ingest.record(device.id, replace(reading, recorded_at=now))
                inserted += 1
            except SensorReadError:
                logger.exception("Sampler could not read device %s", device.id)
        return inserted