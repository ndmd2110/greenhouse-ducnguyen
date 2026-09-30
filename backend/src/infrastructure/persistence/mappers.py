from src.domain.devices.entity import Device
from src.domain.sensors.entity import Sensor
from src.infrastructure.persistence.models import DeviceRow


def device_row_to_domain(row: DeviceRow) -> Device:
    return Device(
        id=row.id,
        device_type=row.device_type,
        role=row.role,
        device_family=row.device_family,
        display_name=row.display_name,
        default_config=row.default_config,
        zone_id=row.zone_id,
        location_id=row.location_id,
        sampling_interval_seconds=row.sampling_interval_seconds,
        tracking_enabled=bool(row.tracking_enabled),
    )


def device_row_to_sensor(row: DeviceRow) -> Sensor:
    return Sensor(
        id=row.id,
        device_type=row.device_type,
        display_name=row.display_name,
        default_config=row.default_config,
        device_family=row.device_family,
        sampling_interval_seconds=row.sampling_interval_seconds,
        tracking_enabled=bool(row.tracking_enabled),
    )