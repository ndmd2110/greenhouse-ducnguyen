"""automation_rules: one active strategy per location

Revision ID: b4e8d2a61c07
Revises: a7d3c9e15b42
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b4e8d2a61c07"
down_revision: Union[str, Sequence[str], None] = "a7d3c9e15b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("strategy_key", sa.String(length=32), nullable=False),
        sa.Column("parameters", sa.JSON().with_variant(JSONB(), "postgresql"), server_default="{}", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("location_id"),
    )


def downgrade() -> None:
    op.drop_table("automation_rules")