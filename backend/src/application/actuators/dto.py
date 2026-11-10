from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApplyRequest(BaseModel):
    command: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ExecutionDto(BaseModel):
    id: UUID
    device_id: UUID
    success: bool
    policy_applied: List[str]
    message: Optional[str] = None
    created_at: datetime