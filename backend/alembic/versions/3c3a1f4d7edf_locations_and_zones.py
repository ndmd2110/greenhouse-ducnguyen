"""locations and zones

Revision ID: 3c3a1f4d7edf
Revises: f9224dba48fe
Create Date: 2026-09-29 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c3a1f4d7edf"
down_revision: Union[str, Sequence[str], None] = "f9224dba48fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "zones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("moisture_threshold_low", sa.Float(), nullable=False),
        sa.Column("moisture_threshold_high", sa.Float(), nullable=False),
        sa.Column("schedule", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_zones_location_id"), "zones", ["location_id"], unique=False)

    op.add_column("devices", sa.Column("zone_id", sa.UUID(), nullable=True))
    op.add_column("devices", sa.Column("location_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_devices_zone_id"), "devices", ["zone_id"], unique=False)
    op.create_index(op.f("ix_devices_location_id"), "devices", ["location_id"], unique=False)
    op.create_foreign_key(
        "fk_devices_zone_id_zones",
        "devices",
        "zones",
        ["zone_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_devices_location_id_locations",
        "devices",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_devices_location_id_locations", "devices", type_="foreignkey")
    op.drop_constraint("fk_devices_zone_id_zones", "devices", type_="foreignkey")
    op.drop_index(op.f("ix_devices_location_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_zone_id"), table_name="devices")
    op.drop_column("devices", "location_id")
    op.drop_column("devices", "zone_id")
    op.drop_index(op.f("ix_zones_location_id"), table_name="zones")
    op.drop_table("zones")
    op.drop_table("locations")
