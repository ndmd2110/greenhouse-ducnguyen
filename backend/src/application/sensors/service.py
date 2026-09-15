from typing import List, Optional
from src.domain.sensors.creators import get_sensor_creator
from src.domain.sensors.entity import Sensor
from src.infrastructure.persistence.device_repository import DeviceRepository

class SensorService:
    def __init__(self, repository: DeviceRepository):
        self.repository = repository

    def create_sensor(self, type_key: str, display_name: Optional[str] = None) -> Sensor:
        creator = get_sensor_creator(type_key)
        sensor = creator.create_sensor(display_name=display_name)
        return self.repository.save_sensor(sensor)

    def list_sensors(self) -> List[Sensor]:
        return self.repository.list_sensors()