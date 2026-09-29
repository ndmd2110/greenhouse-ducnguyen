from __future__ import annotations

from uuid import UUID

from src.domain.devices.entity import Device
from src.infrastructure.persistence.location_repository import LocationRepository


class ZoneAssignmentService:
    def __init__(self, repository: LocationRepository):
        self.repository = repository

    def assign_device_to_zone(self, device_id: UUID, zone_id: UUID | None) -> Device:
        if zone_id is not None:
            zone = self.repository.get_zone(zone_id)
            if zone is None:
                raise ValueError(f"Zone '{zone_id}' was not found.")
        return self.repository.assign_device_to_zone(device_id, zone_id)

    def clear_device_zone(self, device_id: UUID) -> Device:
        return self.repository.clear_device_zone(device_id)
