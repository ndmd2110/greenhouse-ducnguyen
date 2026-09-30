from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.devices.entity import Device
from src.domain.sensors.entity import Sensor
from src.domain.sensors.errors import DeviceNotFoundError
from src.domain.sensors.sampling import initial_sampling_interval
from src.infrastructure.persistence.mappers import device_row_to_domain, device_row_to_sensor
from src.infrastructure.persistence.models import DeviceRow


class DeviceRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_sensor(self, sensor: Sensor) -> Sensor:
        row = DeviceRow(
            id=sensor.id,
            device_type=sensor.device_type,
            role="sensor",
            display_name=sensor.display_name,
            default_config=sensor.default_config,
            # Creators put their interval in default_config; from here on the column is the source of truth.
            sampling_interval_seconds=initial_sampling_interval(sensor.default_config),
            tracking_enabled=True,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)

        sensor.id = row.id
        sensor.device_family = row.device_family
        sensor.sampling_interval_seconds = row.sampling_interval_seconds
        sensor.tracking_enabled = bool(row.tracking_enabled)
        return sensor

    def list_sensors(self) -> List[Sensor]:
        rows = (
            self.session.query(DeviceRow)
            .filter(DeviceRow.role == "sensor")
            .order_by(DeviceRow.created_at.desc())
            .all()
        )
        return [device_row_to_sensor(row) for row in rows]

    def save_device(self, device: Device) -> Device:
        row = DeviceRow(
            id=device.id,
            device_type=device.device_type,
            role=device.role,
            device_family=device.device_family,
            display_name=device.display_name,
            default_config=device.default_config,
            zone_id=device.zone_id,
            location_id=device.location_id,
            sampling_interval_seconds=initial_sampling_interval(
                device.default_config, fallback=device.sampling_interval_seconds
            ),
            tracking_enabled=device.tracking_enabled,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return device_row_to_domain(row)

    def save_devices(self, devices: list[Device]) -> list[Device]:
        return [self.save_device(device) for device in devices]

    def list_devices(
        self,
        *,
        device_family: Optional[str] = None,
        role: Optional[str] = None,
    ) -> list[Device]:
        query = self.session.query(DeviceRow)
        if device_family:
            query = query.filter(DeviceRow.device_family == device_family)
        if role:
            query = query.filter(DeviceRow.role == role)
        rows = query.order_by(DeviceRow.created_at.desc()).all()
        return [device_row_to_domain(row) for row in rows]

    # ---- Phase 5 ----

    def get_device(self, device_id: UUID) -> Optional[Device]:
        row = self.session.get(DeviceRow, device_id)
        return device_row_to_domain(row) if row is not None else None

    def list_tracked_sensors(self) -> list[Device]:
        """Sensors with tracking on. The sampler narrows this further by protocol."""
        rows = (
            self.session.query(DeviceRow)
            .filter(DeviceRow.role == "sensor", DeviceRow.tracking_enabled.is_(True))
            .order_by(DeviceRow.created_at.asc())
            .all()
        )
        return [device_row_to_domain(row) for row in rows]

    def update_sampling(self, device_id: UUID, interval_seconds: int, tracking_enabled: bool) -> Device:
        row = self.session.get(DeviceRow, device_id)
        if row is None:
            raise DeviceNotFoundError(f"Device '{device_id}' was not found.")
        row.sampling_interval_seconds = interval_seconds
        row.tracking_enabled = tracking_enabled
        self.session.commit()
        self.session.refresh(row)
        return device_row_to_domain(row)