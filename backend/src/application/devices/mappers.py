from typing import Optional

from src.application.devices.dto import DeviceDto
from src.domain.actuators.context import ActuatorContext
from src.domain.devices.entity import Device


def map_device_to_dto(device: Device, actuator: Optional[ActuatorContext] = None) -> DeviceDto:
    if device.id is None:
        raise ValueError("Cannot map an unpersisted device")
    return DeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=device.default_config,
        zone_id=device.zone_id,
        location_id=device.location_id,
        sampling_interval_seconds=device.sampling_interval_seconds,
        tracking_enabled=device.tracking_enabled,
        state=actuator.state if actuator is not None else None,
        allowed_commands=actuator.allowed_commands() if actuator is not None else [],
    )