from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str = "embedding"
    status: str
    title: str = "Embedding reindex"
    revision_id: UUID | None = None
    target_concept_id: UUID | None = None
    target_document_id: UUID | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    batch_size: int | None = None
    priority: int
    attempt_count: int
    error_message: str | None = None
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
