from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision_id: UUID
    status: str
    embedding_model: str
    embedding_dimensions: int
    batch_size: int
    priority: int
    attempt_count: int
    error_message: str | None = None
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
