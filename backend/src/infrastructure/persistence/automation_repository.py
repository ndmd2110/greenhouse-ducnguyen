from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.domain.automation.context import ZoneSnapshot
from src.infrastructure.persistence.models import AutomationRuleRow, DeviceRow, LocationRow, ReadingRow, ZoneRow

MOISTURE_DEVICE_TYPE = "moisture_sensor"
LIGHT_DEVICE_TYPE = "light_sensor"


class AutomationRepository:
    def __init__(self, session: Session):
        self.session = session

    # ---- rules ----

    def location_exists(self, location_id: UUID) -> bool:
        return self.session.get(LocationRow, location_id) is not None

    def get_strategy_key(self, location_id: UUID) -> Optional[str]:
        return self.session.execute(
            select(AutomationRuleRow.strategy_key).where(AutomationRuleRow.location_id == location_id)
        ).scalar_one_or_none()

    def upsert_strategy_key(self, location_id: UUID, strategy_key: str) -> str:
        """One row per location (UNIQUE location_id): update it, or insert it."""
        for _ in range(2):  # second pass covers a concurrent insert that beat us to it
            row = self.session.execute(
                select(AutomationRuleRow).where(AutomationRuleRow.location_id == location_id)
            ).scalar_one_or_none()
            if row is not None:
                row.strategy_key = strategy_key
            else:
                self.session.add(AutomationRuleRow(location_id=location_id, strategy_key=strategy_key, parameters={}))
            try:
                self.session.commit()
                return strategy_key
            except IntegrityError:
                self.session.rollback()
        raise RuntimeError("Could not upsert automation rule")

    # ---- context assembly (plain snapshots, never ORM rows) ----

    def list_zone_snapshots(self, location_id: UUID) -> list[ZoneSnapshot]:
        zones = (
            self.session.execute(select(ZoneRow).where(ZoneRow.location_id == location_id).order_by(ZoneRow.name))
            .scalars()
            .all()
        )
        return [
            ZoneSnapshot(
                zone_id=zone.id,
                zone_name=zone.name,
                low=float(zone.moisture_threshold_low),
                high=float(zone.moisture_threshold_high),
                moisture=self._latest_value(zone.id, MOISTURE_DEVICE_TYPE),
                light=self._latest_value(zone.id, LIGHT_DEVICE_TYPE),
            )
            for zone in zones
        ]

    def _latest_value(self, zone_id: UUID, device_type: str) -> Optional[float]:
        """Newest reading among sensors assigned to this zone. Unassigned devices never match."""
        value = self.session.execute(
            select(ReadingRow.value)
            .join(DeviceRow, DeviceRow.id == ReadingRow.device_id)
            .where(
                DeviceRow.zone_id == zone_id,
                DeviceRow.role == "sensor",
                DeviceRow.device_type == device_type,
            )
            .order_by(ReadingRow.recorded_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return float(value) if value is not None else None