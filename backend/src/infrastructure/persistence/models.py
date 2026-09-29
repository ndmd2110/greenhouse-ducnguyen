import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, String
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

    # Phase 4 Zone and Location links
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
