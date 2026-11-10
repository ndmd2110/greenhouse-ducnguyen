from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class ExecutionRecord:
    id: UUID
    device_id: UUID
    success: bool
    policy_applied: list[str]
    message: Optional[str]
    created_at: datetime