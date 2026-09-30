import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.persistence.base import Base

class LocationRow(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    zones = relationship("ZoneRow", back_populates="location", cascade="all, delete-orphan")

class ZoneRow(Base):
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("locations.id", ondelete="CASCADE"), 
        nullable=False,
        index=True,
    )
    name = Column(String(128), nullable=False)
    moisture_threshold_low = Column(Float, nullable=False)
    moisture_threshold_high = Column(Float, nullable=False)
    schedule = Column(JSON, nullable=False, server_default="{}")

    location = relationship("LocationRow", back_populates="zones")

class DeviceRow(Base):
    __tablename__ = "devices"
    __table_args__ = (Index("ix_devices_role", "role"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_type = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False, default="sensor")
    display_name = Column(String(128), nullable=True)
    default_config = Column(JSON, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    device_family = Column(String(32), nullable=False, server_default="simulation", index=True)

    sampling_interval_seconds = Column(Integer, nullable=False, default=300, server_default="300")
    tracking_enabled = Column(Boolean, nullable=False, default=True, server_default=true())

    zone_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("zones.id", ondelete="SET NULL"), 
        nullable=True,
        index=True,
    )
    location_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("locations.id", ondelete="SET NULL"), 
        nullable=True,
        index=True,
    )

    readings = relationship("ReadingRow", back_populates="device", cascade="all, delete-orphan")

class ReadingRow(Base):
    __tablename__ = "sensor_readings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)
    source = Column(String(32), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    device = relationship("DeviceRow", back_populates="readings")


Index("ix_sensor_readings_device_recorded", ReadingRow.device_id, ReadingRow.recorded_at.desc())