"""sensor_readings and device sampling columns

Revision ID: a7d3c9e15b42
Revises: 3c3a1f4d7edf
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a7d3c9e15b42"
down_revision: Union[str, Sequence[str], None] = "3c3a1f4d7edf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MIN_INTERVAL = 5
LEGACY_PROTOCOLS = {"sim": "simulation", "gpio-stub": "mqtt"}


def upgrade() -> None:
    op.add_column("devices", sa.Column("sampling_interval_seconds", sa.Integer(), nullable=False, server_default="300"))
    op.add_column("devices", sa.Column("tracking_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sensor_readings_device_recorded",
        "sensor_readings",
        ["device_id", sa.text("recorded_at DESC")],
    )
    _backfill_devices()


def _backfill_devices() -> None:
    """Python-side backfill so it works on PostgreSQL (JSONB) and SQLite (JSON)."""
    bind = op.get_bind()
    json_type = JSONB() if bind.dialect.name == "postgresql" else sa.JSON()
    devices = sa.table(
        "devices",
        sa.column("id", sa.UUID()),
        sa.column("default_config", json_type),
        sa.column("sampling_interval_seconds", sa.Integer()),
    )
    for device_id, config in bind.execute(sa.select(devices.c.id, devices.c.default_config)).all():
        if isinstance(config, str):
            config = json.loads(config)
        if not isinstance(config, dict):
            continue
        values: dict = {}
        interval = config.get("sampling_interval_seconds")
        if isinstance(interval, (int, float)) and not isinstance(interval, bool) and interval >= MIN_INTERVAL:
            values["sampling_interval_seconds"] = int(interval)
        new_protocol = LEGACY_PROTOCOLS.get(config.get("protocol"))
        if new_protocol is not None:
            values["default_config"] = {**config, "protocol": new_protocol}
        if values:
            bind.execute(sa.update(devices).where(devices.c.id == device_id).values(**values))


def downgrade() -> None:
    op.drop_index("ix_sensor_readings_device_recorded", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_column("devices", "tracking_enabled")
    op.drop_column("devices", "sampling_interval_seconds")