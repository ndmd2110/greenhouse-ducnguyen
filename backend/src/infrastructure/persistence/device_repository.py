from typing import List
from sqlalchemy.orm import Session
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