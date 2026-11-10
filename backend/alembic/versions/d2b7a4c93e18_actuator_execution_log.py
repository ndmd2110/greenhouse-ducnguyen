"""actuator_execution_log: one row per actuator apply attempt

Revision ID: d2b7a4c93e18
Revises: c1a9f0e27d35
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d2b7a4c93e18"
down_revision: Union[str, Sequence[str], None] = "c1a9f0e27d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actuator_execution_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("policy_applied", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_actuator_execution_log_device_id"), "actuator_execution_log", ["device_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_actuator_execution_log_device_id"), table_name="actuator_execution_log")
    op.drop_table("actuator_execution_log")