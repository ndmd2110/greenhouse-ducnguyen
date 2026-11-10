from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.actuators.execution import ExecutionRecord
from src.infrastructure.persistence.models import ActuatorExecutionLogRow


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _to_record(row: ActuatorExecutionLogRow) -> ExecutionRecord:
    return ExecutionRecord(
        id=row.id,
        device_id=row.device_id,
        success=bool(row.success),
        policy_applied=list(row.policy_applied or []),
        message=row.message,
        created_at=_aware(row.created_at),
    )


class ExecutionLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(
        self,
        device_id: UUID,
        *,
        success: bool,
        policy_applied: list[str],
        message: Optional[str],
    ) -> ExecutionRecord:
        row = ActuatorExecutionLogRow(
            device_id=device_id,
            success=success,
            policy_applied=list(policy_applied),
            message=message,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return _to_record(row)

    def list_recent(self, limit: int = 20) -> list[ExecutionRecord]:
        rows = self.session.execute(
            select(ActuatorExecutionLogRow)
            .order_by(ActuatorExecutionLogRow.created_at.desc(), ActuatorExecutionLogRow.id.desc())
            .limit(limit)
        ).scalars().all()
        return [_to_record(row) for row in rows]