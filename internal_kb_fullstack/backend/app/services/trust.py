from __future__ import annotations

from datetime import datetime, timedelta

from app.core.utils import utcnow
from app.schemas.trust import TrustSummary
from app.services.source_urls import canonicalize_source_url

SOURCE_LABELS = {
    "manual": "Workspace note",
    "upload": "Uploaded file",
    "repo": "Repository",
    "github": "GitHub",
    "notion": "Notion",
    "notion-export": "Notion",
    "glossary": "Concept layer",
    "google-drive": "Google Drive",
}

EXTERNAL_SYNC_SOURCES = {"google-drive", "github", "notion", "notion-export", "repo"}


def source_label(source_system: str | None) -> str:
    if not source_system:
        return "Workspace"
    return SOURCE_LABELS.get(source_system, source_system.replace("-", " ").title())


def freshness_state(last_synced_at: datetime | None) -> str:
    if last_synced_at is None:
        return "unknown"
    age = utcnow() - last_synced_at
    if age <= timedelta(days=2):
        return "fresh"
    if age <= timedelta(days=14):
        return "aging"
    return "stale"


def document_authority_kind(*, source_system: str | None, doc_type: str | None = None) -> str:
    if doc_type == "glossary":
        return "approved_concept"
    if source_system in EXTERNAL_SYNC_SOURCES:
        return "synced_source"
    if source_system == "manual":
        return "workspace_note"
    return "workspace_curated"


def build_document_trust(
    *,
    source_system: str | None,
    source_url: str | None,
    source_external_id: str | None = None,
    slug: str | None = None,
    last_synced_at: datetime | None,
    doc_type: str | None = None,
    evidence_count: int = 1,
) -> TrustSummary:
    return TrustSummary(
        source_label=source_label(source_system),
        source_url=canonicalize_source_url(
            source_system=source_system,
            source_url=source_url,
            source_external_id=source_external_id,
            slug=slug,
        ),
        authority_kind=document_authority_kind(source_system=source_system, doc_type=doc_type),
        last_synced_at=last_synced_at,
        freshness_state=freshness_state(last_synced_at),
        evidence_count=max(evidence_count, 1),
    )


def build_concept_trust(
    *,
    status: str,
    source_systems: list[str],
    last_synced_at: datetime | None,
    evidence_count: int,
    source_url: str | None = None,
    source_external_id: str | None = None,
    slug: str | None = None,
) -> TrustSummary:
    if len(source_systems) == 1:
        label = source_label(source_systems[0])
    elif len(source_systems) > 1:
        label = "Multiple sources"
    else:
        label = "Concept layer"
    authority_kind = "approved_concept" if status == "approved" else "candidate_concept"
    return TrustSummary(
        source_label=label,
        source_url=canonicalize_source_url(
            source_system=source_systems[0] if len(source_systems) == 1 else "glossary",
            source_url=source_url,
            source_external_id=source_external_id,
            slug=slug,
        ),
        authority_kind=authority_kind,
        last_synced_at=last_synced_at,
        freshness_state=freshness_state(last_synced_at),
        evidence_count=max(evidence_count, 1),
    )


def build_search_hit_trust(
    *,
    source_system: str | None,
    source_url: str | None,
    source_external_id: str | None = None,
    slug: str | None = None,
    last_synced_at: datetime | None,
    evidence_count: int = 1,
    matched_concept: bool = False,
) -> TrustSummary:
    authority_kind = "concept_evidence" if matched_concept else document_authority_kind(source_system=source_system)
    return TrustSummary(
        source_label=source_label(source_system),
        source_url=canonicalize_source_url(
            source_system=source_system,
            source_url=source_url,
            source_external_id=source_external_id,
            slug=slug,
        ),
        authority_kind=authority_kind,
        last_synced_at=last_synced_at,
        freshness_state=freshness_state(last_synced_at),
        evidence_count=max(evidence_count, 1),
    )
