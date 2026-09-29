from __future__ import annotations

from uuid import UUID

from src.application.locations.dto import LocationConfigResponse, LocationCreateRequest, LocationSummaryResponse, ZoneCreateRequest, ZoneResponse, ZoneUpdateRequest
from src.application.locations.mappers import location_config_to_dto, zone_to_dto
from src.domain.locations.config_builder import LocationConfigBuilder
from src.domain.locations.errors import ConfigurationError
from src.infrastructure.persistence.location_repository import LocationRepository


class LocationConfigService:
    def __init__(self, repository: LocationRepository):
        self.repository = repository

    def create_location_config(self, payload: LocationCreateRequest) -> LocationConfigResponse:
        if not payload.location_name or not payload.location_name.strip():
            raise ConfigurationError("Location name is required and cannot be empty.")
        if not payload.zones:
            raise ConfigurationError("Location must contain at least one zone.")

        builder = LocationConfigBuilder().with_location_name(payload.location_name)
        for zone in payload.zones:
            builder.add_zone(
                zone.name,
                zone.moisture_threshold_low,
                zone.moisture_threshold_high,
                zone.schedule,
            )

        config = builder.build()
        saved = self.repository.create_location_config(config)
        return location_config_to_dto(saved)

    def list_locations(self) -> list[LocationSummaryResponse]:
        rows = self.repository.list_locations()
        return [LocationSummaryResponse(id=row.id, name=row.name) for row in rows]

    def get_location_config(self, location_id: UUID) -> LocationConfigResponse:
        config = self.repository.get_location_config(location_id)
        return location_config_to_dto(config)

    def delete_location(self, location_id: UUID) -> None:
        self.repository.delete_location(location_id)

    def add_zone(self, location_id: UUID, payload: ZoneCreateRequest) -> ZoneResponse:
        self._validate_zone_payload(payload)
        zone = self.repository.add_zone(location_id, payload)
        return zone_to_dto(zone)

    def update_zone(self, location_id: UUID, zone_id: UUID, payload: ZoneUpdateRequest) -> ZoneResponse:
        self._validate_zone_payload(payload)
        zone = self.repository.update_zone(location_id, zone_id, payload)
        return zone_to_dto(zone)

    def delete_zone(self, location_id: UUID, zone_id: UUID) -> None:
        config = self.repository.get_location_config(location_id)
        if len(config.location.zones) <= 1:
            raise ConfigurationError("A location must retain at least one zone.")
        self.repository.delete_zone(location_id, zone_id)

    def get_zone_devices(self, location_id: UUID, zone_id: UUID):
        return self.repository.get_zone_devices(location_id, zone_id)

    @staticmethod
    def _validate_zone_payload(payload: ZoneCreateRequest | ZoneUpdateRequest) -> None:
        if not payload.name or not payload.name.strip():
            raise ConfigurationError("Zone name cannot be empty.")
        if not (0.0 <= payload.moisture_threshold_low <= 1.0):
            raise ConfigurationError(
                f"Zone '{payload.name}' low threshold ({payload.moisture_threshold_low}) must be between 0.0 and 1.0."
            )
        if not (0.0 <= payload.moisture_threshold_high <= 1.0):
            raise ConfigurationError(
                f"Zone '{payload.name}' high threshold ({payload.moisture_threshold_high}) must be between 0.0 and 1.0."
            )
        if payload.moisture_threshold_low >= payload.moisture_threshold_high:
            raise ConfigurationError(
                f"Zone '{payload.name}' low threshold ({payload.moisture_threshold_low}) must be strictly less than high threshold ({payload.moisture_threshold_high})."
            )
