from abc import ABC, abstractmethod

from src.domain.devices.entity import Device
from src.domain.sensors.reading import Reading


class SensorPort(ABC):
    @abstractmethod
    def read(self, device: Device) -> Reading:
        """Return one normalized reading for the device."""