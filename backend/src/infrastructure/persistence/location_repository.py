from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.application.devices.dto import DeviceDto
from src.application.locations.dto import ZoneCreateRequest, ZoneUpdateRequest
from src.domain.devices.entity import Device
from src.domain.locations.entity import Location, LocationConfig, Zone
from src.infrastructure.persistence.models import DeviceRow, LocationRow, ZoneRow
from src.infrastructure.persistence.mappers import device_row_to_domain


class LocationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_location_config(self, location_config: LocationConfig) -> LocationConfig:
        location = location_config.location
        location_row = LocationRow(name=location.name)
        self.session.add(location_row)
        self.session.flush()

        saved_zones: list[Zone] = []
        for zone in location.zones:
            zone_row = ZoneRow(
                name=zone.name,
                location_id=location_row.id,
                moisture_threshold_low=zone.moisture_threshold_low,
                moisture_threshold_high=zone.moisture_threshold_high,
                schedule=zone.schedule,
            )
            self.session.add(zone_row)
            self.session.flush()
            saved_zones.append(
                Zone(
                    id=zone_row.id,
                    name=zone_row.name,
                    moisture_threshold_low=zone_row.moisture_threshold_low,
                    moisture_threshold_high=zone_row.moisture_threshold_high,
                    schedule=zone_row.schedule or {},
                    location_id=zone_row.location_id,
                )
            )

        self.session.commit()
        return LocationConfig(
            location=Location(
                id=location_row.id,
                name=location_row.name,
                zones=tuple(saved_zones),
            )
        )

    def list_locations(self) -> list[LocationRow]:
        return (
            self.session.query(LocationRow)
            .order_by(LocationRow.created_at.desc())
            .all()
        )

    def get_location_config(self, location_id: UUID) -> LocationConfig:
        location_row = self.session.get(LocationRow, location_id)
        if location_row is None:
            raise KeyError(f"Location '{location_id}' was not found.")

        zone_rows = (
            self.session.query(ZoneRow)
            .filter(ZoneRow.location_id == location_id)
            .order_by(ZoneRow.id.asc())
            .all()
        )

        zones = [
            Zone(
                id=row.id,
                name=row.name,
                moisture_threshold_low=row.moisture_threshold_low,
                moisture_threshold_high=row.moisture_threshold_high,
                schedule=row.schedule or {},
                location_id=row.location_id,
            )
            for row in zone_rows
        ]
        return LocationConfig(
            location=Location(
                id=location_row.id,
                name=location_row.name,
                zones=tuple(zones),
            )
        )

    def delete_location(self, location_id: UUID) -> None:
        self.session.query(DeviceRow).filter(DeviceRow.location_id == location_id).update(
            {"zone_id": None, "location_id": None},
            synchronize_session=False,
        )
        location_row = self.session.get(LocationRow, location_id)
        if location_row is None:
            raise KeyError(f"Location '{location_id}' was not found.")
        self.session.delete(location_row)
        self.session.commit()

    def add_zone(self, location_id: UUID, payload: ZoneCreateRequest) -> Zone:
        location_row = self.session.get(LocationRow, location_id)
        if location_row is None:
            raise KeyError(f"Location '{location_id}' was not found.")

        row = ZoneRow(
            name=payload.name.strip(),
            location_id=location_row.id,
            moisture_threshold_low=payload.moisture_threshold_low,
            moisture_threshold_high=payload.moisture_threshold_high,
            schedule=payload.schedule or {},
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return Zone(
            id=row.id,
            name=row.name,
            moisture_threshold_low=row.moisture_threshold_low,
            moisture_threshold_high=row.moisture_threshold_high,
            schedule=row.schedule or {},
            location_id=row.location_id,
        )

    def update_zone(self, location_id: UUID, zone_id: UUID, payload: ZoneUpdateRequest) -> Zone:
        row = self.session.get(ZoneRow, zone_id)
        if row is None or row.location_id != location_id:
            raise KeyError(f"Zone '{zone_id}' was not found in location '{location_id}'.")

        row.name = payload.name.strip()
        row.moisture_threshold_low = payload.moisture_threshold_low
        row.moisture_threshold_high = payload.moisture_threshold_high
        row.schedule = payload.schedule or {}
        self.session.commit()
        self.session.refresh(row)
        return Zone(
            id=row.id,
            name=row.name,
            moisture_threshold_low=row.moisture_threshold_low,
            moisture_threshold_high=row.moisture_threshold_high,
            schedule=row.schedule or {},
            location_id=row.location_id,
        )

    def delete_zone(self, location_id: UUID, zone_id: UUID) -> None:
        row = self.session.get(ZoneRow, zone_id)
        if row is None or row.location_id != location_id:
            raise KeyError(f"Zone '{zone_id}' was not found in location '{location_id}'.")

        self.session.query(DeviceRow).filter(DeviceRow.zone_id == zone_id).update(
            {"zone_id": None, "location_id": None},
            synchronize_session=False,
        )
        self.session.delete(row)
        self.session.commit()

    def get_zone(self, zone_id: UUID) -> Zone | None:
        row = self.session.get(ZoneRow, zone_id)
        if row is None:
            return None
        return Zone(
            id=row.id,
            name=row.name,
            moisture_threshold_low=row.moisture_threshold_low,
            moisture_threshold_high=row.moisture_threshold_high,
            schedule=row.schedule or {},
            location_id=row.location_id,
        )

    def assign_device_to_zone(self, device_id: UUID, zone_id: UUID | None) -> Device:
        row = self.session.get(DeviceRow, device_id)
        if row is None:
            raise KeyError(f"Device '{device_id}' was not found.")
        if zone_id is None:
            row.zone_id = None
            row.location_id = None
        else:
            zone = self.session.get(ZoneRow, zone_id)
            if zone is None:
                raise KeyError(f"Zone '{zone_id}' was not found.")
            row.zone_id = zone.id
            row.location_id = zone.location_id
        self.session.commit()
        self.session.refresh(row)
        return device_row_to_domain(row)

    def clear_device_zone(self, device_id: UUID) -> Device:
        return self.assign_device_to_zone(device_id, None)

    def get_zone_devices(self, location_id: UUID, zone_id: UUID) -> list[Device]:
        zone = self.session.get(ZoneRow, zone_id)
        if zone is None or zone.location_id != location_id:
            raise KeyError(f"Zone '{zone_id}' was not found in location '{location_id}'.")

        rows = (
            self.session.query(DeviceRow)
            .filter(DeviceRow.zone_id == zone_id)
            .order_by(DeviceRow.created_at.desc())
            .all()
        )
        return [
            device_row_to_domain(row)
            for row in rows
        ]

    def get_device_by_id(self, device_id: UUID) -> Device | None:
        row = self.session.get(DeviceRow, device_id)
        if row is None:
            return None
        return device_row_to_domain(row)

    @staticmethod
    def map_device_row_to_dto(device: Device) -> DeviceDto:
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
