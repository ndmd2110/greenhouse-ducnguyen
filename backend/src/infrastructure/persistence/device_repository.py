from typing import List, Optional
from sqlalchemy.orm import Session

from src.domain.devices.entity import Device
from src.domain.sensors.entity import Sensor
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
            default_config=sensor.default_config
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        
        sensor.id = row.id
        return sensor

    def list_sensors(self) -> List[Sensor]:
        rows = (
            self.session.query(DeviceRow)
            .filter(DeviceRow.role == "sensor")
            .order_by(DeviceRow.created_at.desc())
            .all()
        )
        return [
            Sensor(
                id=row.id,
                device_type=row.device_type,
                display_name=row.display_name,
                default_config=row.default_config
            )
            for row in rows
        ]

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
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return Device(
            id=row.id,
            device_type=row.device_type,
            role=row.role,
            device_family=row.device_family,
            display_name=row.display_name,
            default_config=row.default_config,
            zone_id=row.zone_id,
            location_id=row.location_id,
        )

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
        return [
            Device(
                id=row.id,
                device_type=row.device_type,
                role=row.role,
                device_family=row.device_family,
                display_name=row.display_name,
                default_config=row.default_config,
                zone_id=row.zone_id,
                location_id=row.location_id,
            )
            for row in rows
        ]