from abc import ABC, abstractmethod
from typing import List
from src.domain.sensors.creators import get_sensor_creator
from .entity import Device

class DeviceFamilyFactory(ABC):
    @property
    @abstractmethod
    def family_key(self) -> str:
        pass

    @abstractmethod
    def create_device_set(self) -> List[Device]:
        """Returns a cohesive kit of sensors and actuators."""
        pass

class SimulationFactory(DeviceFamilyFactory):
    @property
    def family_key(self) -> str:
        return "simulation"

    def create_device_set(self) -> List[Device]:
        return _create_family_devices(
            family=self.family_key,
            protocol="simulation",
            sensor_names=("Sim soil moisture", "Sim ambient light"),
            actuator_names=("Sim irrigation pump", "Sim grow light"),
        )


class EdgeFactory(DeviceFamilyFactory):
    @property
    def family_key(self) -> str:
        return "edge"

    def create_device_set(self) -> List[Device]:
        return _create_family_devices(
            family=self.family_key,
            protocol="mqtt",
            sensor_names=("Edge soil moisture", "Edge ambient light"),
            actuator_names=("Edge irrigation pump", "Edge grow light"),
        )


def _create_family_devices(
    *, family: str, protocol: str, sensor_names: tuple[str, str], actuator_names: tuple[str, str]
) -> List[Device]:
    sensor_types = ("moisture", "light")
    sensors = [
        get_sensor_creator(sensor_type).create_sensor(display_name=display_name)
        for sensor_type, display_name in zip(sensor_types, sensor_names)
    ]
    devices = [
        Device(
            id=sensor.id,
            device_type=sensor.device_type,
            role="sensor",
            device_family=family,
            display_name=sensor.display_name,
            default_config={**sensor.default_config, "protocol": protocol},
        )
        for sensor in sensors
    ]
    devices.extend(
        [
            Device(
                id=None,
                device_type=device_type,
                role="actuator",
                device_family=family,
                display_name=display_name,
                default_config={"protocol": protocol},
            )
            for device_type, display_name in zip(
                ("water_pump", "grow_light"), actuator_names
            )
        ]
    )
    return devices