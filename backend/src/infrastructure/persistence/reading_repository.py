from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.sensors.reading import Reading
from src.infrastructure.persistence.models import ReadingRow


def _as_utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for timezone=True columns; we always store UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _row_to_reading(row: ReadingRow) -> Reading:
    return Reading(
        device_id=row.device_id,
        value=float(row.value),
        unit=row.unit,
        source=row.source,
        recorded_at=_as_utc(row.recorded_at),
    )


class ReadingRepository:
    def __init__(self, session: Session):
        self.session = session

    def insert(self, reading: Reading) -> Reading:
        row = ReadingRow(
            device_id=reading.device_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return _row_to_reading(row)

    def list_for_device(self, device_id: UUID, limit: int = 20) -> list[Reading]:
        rows = (
            self.session.execute(
                select(ReadingRow)
                .where(ReadingRow.device_id == device_id)
                .order_by(ReadingRow.recorded_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [_row_to_reading(row) for row in rows]

    def latest_recorded_at(self, device_id: UUID) -> Optional[datetime]:
        latest = self.list_for_device(device_id, limit=1)
        return latest[0].recorded_at if latest else None