from __future__ import annotations

from src.application.locations.dto import LocationConfigResponse, LocationSummaryResponse, ZoneResponse
from src.domain.locations.entity import LocationConfig, Zone


def zone_to_dto(zone: Zone) -> ZoneResponse:
    if zone.id is None:
        raise ValueError("Cannot map an unsaved zone to a response DTO.")
    if zone.location_id is None:
        raise ValueError("Zone is missing its location_id.")
    return ZoneResponse(
        id=zone.id,
        location_id=zone.location_id,
        name=zone.name,
        moisture_threshold_low=zone.moisture_threshold_low,
        moisture_threshold_high=zone.moisture_threshold_high,
        schedule=zone.schedule,
    )


def location_config_to_dto(config: LocationConfig) -> LocationConfigResponse:
    location = config.location
    if location.id is None:
        raise ValueError("Cannot map an unsaved location to a response DTO.")
    return LocationConfigResponse(
        location=LocationSummaryResponse(id=location.id, name=location.name),
        zones=[zone_to_dto(zone) for zone in location.zones],
    )
