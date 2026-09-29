# backend/src/domain/locations/config_builder.py
from typing import List, Dict, Any, Optional
from .entity import Location, Zone, LocationConfig
from .errors import ConfigurationError

class LocationConfigBuilder:
    def __init__(self) -> None:
        self._name: Optional[str] = None
        self._zones: List[Zone] = []

    def with_location_name(self, name: str) -> "LocationConfigBuilder":
        self._name = name
        return self

    def set_name(self, name: str) -> "LocationConfigBuilder":
        return self.with_location_name(name)

    def add_zone(
        self,
        name: str,
        moisture_threshold_low: float,
        moisture_threshold_high: float,
        schedule: Optional[Dict[str, Any]] = None
    ) -> "LocationConfigBuilder":
        zone = Zone(
            name=name.strip() if name else name,
            moisture_threshold_low=moisture_threshold_low,
            moisture_threshold_high=moisture_threshold_high,
            schedule=schedule or {}
        )
        self._zones.append(zone)
        return self

    def build(self) -> LocationConfig:
        if not self._name or not self._name.strip():
            raise ConfigurationError("Location name is required and cannot be empty.")

        if not self._zones:
            raise ConfigurationError("Location must contain at least one zone.")

        zone_names = set()
        for zone in self._zones:
            if not zone.name or not zone.name.strip():
                raise ConfigurationError("Zone name cannot be empty.")

            stripped_name = zone.name.strip()
            if stripped_name in zone_names:
                raise ConfigurationError(f"Duplicate zone name '{zone.name}' in location.")
            zone_names.add(stripped_name)

            low = zone.moisture_threshold_low
            high = zone.moisture_threshold_high

            if not (0.0 <= low <= 1.0):
                raise ConfigurationError(f"Zone '{zone.name}' low threshold ({low}) must be between 0.0 and 1.0.")

            if not (0.0 <= high <= 1.0):
                raise ConfigurationError(f"Zone '{zone.name}' high threshold ({high}) must be between 0.0 and 1.0.")

            if low >= high:
                raise ConfigurationError(f"Zone '{zone.name}' low threshold ({low}) must be strictly less than high threshold ({high}).")

        location = Location(
            name=self._name.strip(),
            zones=tuple(self._zones)
        )
        return LocationConfig(location=location)