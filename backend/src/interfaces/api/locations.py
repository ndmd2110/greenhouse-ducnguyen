from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.devices.dto import DeviceDto
from src.application.locations.config_service import LocationConfigService
from src.application.locations.dto import DeviceZoneAssignmentRequest, LocationConfigResponse, LocationCreateRequest, LocationSummaryResponse, ZoneCreateRequest, ZoneResponse, ZoneUpdateRequest
from src.application.locations.zone_assignment_service import ZoneAssignmentService
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.location_repository import LocationRepository

router = APIRouter(prefix="/api", tags=["locations"])


def get_location_service(db: Session = Depends(get_db)) -> LocationConfigService:
    return LocationConfigService(LocationRepository(db))


def get_zone_assignment_service(db: Session = Depends(get_db)) -> ZoneAssignmentService:
    return ZoneAssignmentService(LocationRepository(db))


@router.get("/locations", response_model=list[LocationSummaryResponse])
def list_locations(service: LocationConfigService = Depends(get_location_service)):
    return service.list_locations()


@router.post("/locations/config", response_model=LocationConfigResponse, status_code=status.HTTP_201_CREATED)
@router.post("/locations", response_model=LocationConfigResponse, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreateRequest, service: LocationConfigService = Depends(get_location_service)):
    try:
        return service.create_location_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/locations/{location_id}/config", response_model=LocationConfigResponse)
def get_location_config(location_id: UUID, service: LocationConfigService = Depends(get_location_service)):
    try:
        return service.get_location_config(location_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: UUID, service: LocationConfigService = Depends(get_location_service)):
    try:
        service.delete_location(location_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/locations/{location_id}/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def add_zone(location_id: UUID, payload: ZoneCreateRequest, service: LocationConfigService = Depends(get_location_service)):
    try:
        return service.add_zone(location_id, payload)
    except (KeyError, ValueError) as exc:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, KeyError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/locations/{location_id}/zones/{zone_id}", response_model=ZoneResponse)
def update_zone(location_id: UUID, zone_id: UUID, payload: ZoneUpdateRequest, service: LocationConfigService = Depends(get_location_service)):
    try:
        return service.update_zone(location_id, zone_id, payload)
    except (KeyError, ValueError) as exc:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, KeyError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete("/locations/{location_id}/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(location_id: UUID, zone_id: UUID, service: LocationConfigService = Depends(get_location_service)):
    try:
        service.delete_zone(location_id, zone_id)
    except (KeyError, ValueError) as exc:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, KeyError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/devices/{id}/zone", response_model=DeviceDto)
def assign_device_zone(id: UUID, payload: DeviceZoneAssignmentRequest, service: ZoneAssignmentService = Depends(get_zone_assignment_service)):
    try:
        device = service.assign_device_to_zone(id, payload.zone_id)
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
    except (KeyError, ValueError) as exc:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, KeyError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/locations/{location_id}/zones/{zone_id}/devices", response_model=list[DeviceDto])
def list_zone_devices(location_id: UUID, zone_id: UUID, service: LocationConfigService = Depends(get_location_service)):
    try:
        devices = service.get_zone_devices(location_id, zone_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [
        DeviceDto(
            id=device.id,
            device_type=device.device_type,
            role=device.role,
            device_family=device.device_family,
            display_name=device.display_name,
            default_config=device.default_config,
            zone_id=device.zone_id,
            location_id=device.location_id,
        )
        for device in devices
    ]
