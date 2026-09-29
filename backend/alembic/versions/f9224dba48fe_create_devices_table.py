"""create devices table

Revision ID: f9224dba48fe
Revises: e5b18f32b230
Create Date: 2026-09-23 15:03:23.763609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f9224dba48fe'
down_revision: Union[str, Sequence[str], None] = 'e5b18f32b230'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "devices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("device_type", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column(
            "default_config",
            JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "device_family",
            sa.String(length=32),
            server_default="simulation",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_role", "devices", ["role"], unique=False)
    op.create_index("ix_devices_family", "devices", ["device_family"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_devices_family", table_name="devices")
    op.drop_index("ix_devices_role", table_name="devices")
    op.drop_table("devices")
