from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.actuators.context import ActuatorContext
from src.domain.actuators.state import INITIAL_STATE
from src.infrastructure.persistence.models import ActuatorStateRow


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; everything we store is UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _to_context(row: ActuatorStateRow) -> ActuatorContext:
    return ActuatorContext(device_id=row.device_id, state=row.state, updated_at=_aware(row.updated_at))


class ActuatorStateRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, device_id: UUID) -> Optional[ActuatorContext]:
        row = self.session.get(ActuatorStateRow, device_id)
        return _to_context(row) if row is not None else None

    def get_or_create(self, device_id: UUID) -> ActuatorContext:
        """Actuators that predate Phase 8 resolve to idle and get their row on first touch."""
        row = self.session.get(ActuatorStateRow, device_id)
        if row is None:
            row = ActuatorStateRow(device_id=device_id, state=INITIAL_STATE, updated_at=datetime.now(timezone.utc))
            self.session.add(row)
            self.session.commit()
            self.session.refresh(row)
        return _to_context(row)

    def get_many(self, device_ids: Iterable[UUID]) -> dict[UUID, ActuatorContext]:
        ids = list(device_ids)
        if not ids:
            return {}
        rows = self.session.execute(
            select(ActuatorStateRow).where(ActuatorStateRow.device_id.in_(ids))
        ).scalars().all()
        found = {row.device_id: row for row in rows}
        created = False
        for device_id in ids:
            if device_id not in found:
                row = ActuatorStateRow(
                    device_id=device_id, state=INITIAL_STATE, updated_at=datetime.now(timezone.utc)
                )
                self.session.add(row)
                found[device_id] = row
                created = True
        if created:
            self.session.commit()
        return {device_id: _to_context(found[device_id]) for device_id in ids}

    def save(self, context: ActuatorContext) -> None:
        row = self.session.get(ActuatorStateRow, context.device_id)
        if row is None:
            row = ActuatorStateRow(device_id=context.device_id)
            self.session.add(row)
        row.state = context.state
        row.updated_at = context.updated_at
        self.session.commit()