import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.infrastructure.persistence.base import Base

class DeviceRow(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_type = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False, default="sensor")
    display_name = Column(String(128), nullable=True)
    default_config = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_devices_role", "role"),
    )