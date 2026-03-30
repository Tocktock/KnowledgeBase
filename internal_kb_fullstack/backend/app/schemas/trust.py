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


class VerificationSummary(BaseModel):
    status: str
    policy_label: str | None = None
    policy_version: int | None = None
    evidence_bundle_hash: str | None = None
    verified_at: datetime | None = None
    due_at: datetime | None = None
    last_checked_at: datetime | None = None
    verified_by: str | None = None
    reason: str | None = None
