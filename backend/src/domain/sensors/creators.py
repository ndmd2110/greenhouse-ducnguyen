from abc import ABC, abstractmethod
from typing import Dict, Type, Optional
from src.domain.sensors.entity import Sensor

class SensorCreator(ABC):
    @abstractmethod
    def create_sensor(self, display_name: Optional[str] = None) -> Sensor:
        pass

class MoistureSensorCreator(SensorCreator):
    def create_sensor(self, display_name: Optional[str] = None) -> Sensor:
        name = display_name if display_name else "Soil Moisture Sensor"
        default_config = {
            "unit": "percentage",
            "sampling_interval_seconds": 60,
            "moisture_threshold_low": 20.0,
            "moisture_threshold_high": 80.0,
        }
        return Sensor(
            device_type="moisture_sensor",
            display_name=name,
            default_config=default_config
        )

class LightSensorCreator(SensorCreator):
    def create_sensor(self, display_name: Optional[str] = None) -> Sensor:
        name = display_name if display_name else "Ambient Light Sensor"
        default_config = {
            "unit": "lux",
            "sampling_interval_seconds": 30,
            "gain_mode": "auto",
            "lux_threshold_low": 100,
        }
        return Sensor(
            device_type="light_sensor",
            display_name=name,
            default_config=default_config
        )

SENSOR_CREATORS: Dict[str, Type[SensorCreator]] = {
    "moisture": MoistureSensorCreator,
    "light": LightSensorCreator,
}

def get_sensor_creator(sensor_type: str) -> SensorCreator:
    creator_cls = SENSOR_CREATORS.get(sensor_type.lower())
    if not creator_cls:
        raise ValueError(f"Unknown sensor type: '{sensor_type}'. Valid types are: {list(SENSOR_CREATORS.keys())}")
    return creator_cls()