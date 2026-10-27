from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.automation.service import AutomationService
from src.application.overview.dto import (
    DeviceCountsDto,
    LocationOverviewDto,
    LocationSummaryDto,
    OverviewDeviceDto,
    OverviewReadingDto,
    OverviewRecommendationDto,
    OverviewZoneDto,
)
from src.domain.automation.errors import LocationNotFoundError
from src.infrastructure.persistence.automation_repository import AutomationRepository
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository


class LocationOverviewFacade:
    """One read entry point over locations, assigned devices, readings and the saved strategy."""

    def __init__(
        self,
        locations: LocationRepository,
        devices: DeviceRepository,
        readings: ReadingRepository,
        automation_repo: AutomationRepository,
        automation: AutomationService,
    ) -> None:
        self._locations = locations
        self._devices = devices
        self._readings = readings
        self._automation_repo = automation_repo
        self._automation = automation

    @classmethod
    def from_session(cls, session: Session) -> "LocationOverviewFacade":
        # Wiring lives here so the HTTP handler never imports a repository.
        automation_repo = AutomationRepository(session)
        return cls(
            LocationRepository(session),
            DeviceRepository(session),
            ReadingRepository(session),
            automation_repo,
            AutomationService(automation_repo),
        )

    def get_overview(self, location_id: UUID) -> LocationOverviewDto:
        # 1. location + every zone
        try:
            location = self._locations.get_location_config(location_id).location
        except KeyError as exc:
            raise LocationNotFoundError(str(exc)) from exc

        # 2. assigned devices only (location_id set AND zone_id not null)
        assigned = self._devices.list_assigned_to_location(location_id)

        # 3. newest reading per assigned device, one query, any source
        latest = self._readings.latest_for_devices([d.id for d in assigned])

        devices_by_zone = defaultdict(list)
        for device in assigned:
            devices_by_zone[device.zone_id].append(device)

        zones: list[OverviewZoneDto] = []
        for zone in sorted(location.zones, key=lambda z: z.name):
            zone_devices = devices_by_zone.get(zone.id, [])
            zones.append(
                OverviewZoneDto(
                    id=zone.id,
                    name=zone.name,
                    moisture_threshold_low=zone.moisture_threshold_low,
                    moisture_threshold_high=zone.moisture_threshold_high,
                    devices=[
                        OverviewDeviceDto(
                            id=d.id, device_type=d.device_type, role=d.role, display_name=d.display_name
                        )
                        for d in zone_devices
                    ],
                    latest_readings=[
                        OverviewReadingDto(
                            device_id=d.id,
                            value=latest[d.id].value,
                            unit=latest[d.id].unit,
                            recorded_at=latest[d.id].recorded_at,
                            tracking_enabled=d.tracking_enabled,
                            sampling_interval_seconds=d.sampling_interval_seconds,
                        )
                        for d in zone_devices
                        if d.id in latest  # device with no row stays in devices, omitted here
                    ],
                )
            )

        counts = DeviceCountsDto(
            sensor=sum(1 for d in assigned if d.role == "sensor"),
            actuator=sum(1 for d in assigned if d.role == "actuator"),
        )

        # 4. saved key; 5. evaluate only when a key exists (computed per GET, never stored)
        key = self._automation_repo.get_strategy_key(location_id)
        recommendation = None
        if key:
            # evaluate still loads moisture once per zone inside the strategy service.
            rec = self._automation.evaluate(location_id, key)
            recommendation = OverviewRecommendationDto(action=rec.action, reason=rec.reason)

        return LocationOverviewDto(
            location=LocationSummaryDto(id=location.id, name=location.name),
            device_counts=counts,
            zones=zones,
            strategy_key=key,
            last_recommendation=recommendation,
        )