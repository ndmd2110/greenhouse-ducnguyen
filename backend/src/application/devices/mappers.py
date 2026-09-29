from src.application.devices.dto import DeviceDto
from src.domain.devices.entity import Device


def map_device_to_dto(device: Device) -> DeviceDto:
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
    )
