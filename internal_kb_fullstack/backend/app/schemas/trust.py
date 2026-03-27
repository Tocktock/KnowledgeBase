from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrustSummary(BaseModel):
    source_label: str
    source_url: str | None = None
    authority_kind: str
    last_synced_at: datetime | None = None
    freshness_state: str
    evidence_count: int = 1
