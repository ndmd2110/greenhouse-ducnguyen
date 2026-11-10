"""actuator_states: persisted lifecycle state per actuator (seeded to idle in upgrade())

Revision ID: c1a9f0e27d35
Revises: b4e8d2a61c07
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a9f0e27d35"
down_revision: Union[str, Sequence[str], None] = "b4e8d2a61c07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actuator_states",
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id"),
    )
    # Seed: every existing actuator starts idle (done here, in the migration).
    op.execute(
        "INSERT INTO actuator_states (device_id, state, updated_at) "
        "SELECT id, 'idle', CURRENT_TIMESTAMP FROM devices WHERE role = 'actuator'"
    )


def downgrade() -> None:
    op.drop_table("actuator_states")