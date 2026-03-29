from __future__ import annotations

from datetime import datetime
import math
import re
from hashlib import sha256
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Text, case, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import normalize_whitespace, slugify, utcnow
from app.db.models import (
    ConceptStatus,
    ConceptSupport,
    ConceptType,
    ConnectorConnection,
    ConnectorOwnerScope,
    ConnectorResource,
    ConnectorResourceStatus,
    ConnectorSourceItem,
    ConnectorSourceItemStatus,
    Document,
    DocumentChunk,
    DocumentVisibilityScope,
    GlossaryJob,
    GlossaryJobKind,
    GlossaryJobScope,
    GlossaryValidationRun,
    GlossaryValidationState,
    JobStatus,
    KnowledgeConcept,
)
from app.schemas.glossary import (
    GlossaryConceptDetailResponse,
    GlossaryConceptDocumentLink,
    GlossaryConceptListResponse,
    GlossaryConceptRequestCreateRequest,
    GlossaryConceptRequestListEntry,
    GlossaryConceptRequestListItem,
    GlossaryConceptRequestListResponse,
    GlossaryConceptRequestResponse,
    GlossaryConceptSummary,
    GlossaryConceptUpdateRequest,
    GlossaryDraftRequest,
    GlossarySupportItem,
    GlossaryValidationRunCreateRequest,
    GlossaryValidationRunListResponse,
    GlossaryValidationRunSummary,
)
from app.services.trust import build_concept_trust, build_document_trust

NOISE_PATTERN = re.compile(
    r"(회의|회고|작업|공유|콘텐츠|에셋|신청|테스트|클론|정리|초안|리뷰|가이드|업무 목록|issue|ticket|retro|meeting)",
    flags=re.IGNORECASE,
)
TEAM_PATTERN = re.compile(r"(팀|스쿼드|squad|team)", flags=re.IGNORECASE)
METRIC_PATTERN = re.compile(r"(율|전환|지표|metric|rate|kpi|비율)", flags=re.IGNORECASE)
PROCESS_PATTERN = re.compile(r"(프로세스|절차|workflow|운영|정책|process|flow)", flags=re.IGNORECASE)
PRODUCT_PATTERN = re.compile(r"(센디|차량|오더|화주|기사|dispatch|delivery|product|feature)", flags=re.IGNORECASE)
TABLE_SPLIT_PATTERN = re.compile(r"\s*,\s*|\s*\|\s*|\s*\t\s*")
HEX_SUFFIX_PATTERN = re.compile(r"(?:-\d+)?-[0-9a-f]{10}$")
ORDINAL_SUFFIX_PATTERN = re.compile(r"\s+\(\d+\)$")


@dataclass(slots=True)
class CandidateSupport:
    document_id: UUID
    revision_id: UUID | None
    chunk_id: UUID | None
    document_slug: str
    document_title: str
    document_status: str
    document_doc_type: str
    owner_team: str | None
    support_group_key: str
    evidence_kind: str
    evidence_term: str
    support_text: str
    evidence_strength: float
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateConcept:
    normalized_term: str
    display_counter: Counter[str] = field(default_factory=Counter)
    aliases: set[str] = field(default_factory=set)
    supports: dict[tuple[UUID, UUID | None, str, str], CandidateSupport] = field(default_factory=dict)
    document_ids: set[UUID] = field(default_factory=set)
    chunk_ids: set[UUID] = field(default_factory=set)
    owner_teams: Counter[str] = field(default_factory=Counter)
    source_systems: set[str] = field(default_factory=set)
    evidence_kinds: Counter[str] = field(default_factory=Counter)
    title_hits: int = 0

    def add_support(self, *, display_term: str, source_system: str, support: CandidateSupport) -> None:
        self.display_counter[display_term] += 1
        self.aliases.add(display_term)
        self.source_systems.add(source_system)
        if support.owner_team:
            self.owner_teams[support.owner_team] += 1
        self.evidence_kinds[support.evidence_kind] += 1
        if support.evidence_kind == "title":
            self.title_hits += 1
        self.document_ids.add(support.document_id)
        if support.chunk_id is not None:
            self.chunk_ids.add(support.chunk_id)
        key = (support.document_id, support.chunk_id, support.evidence_kind, support.evidence_term)
        existing = self.supports.get(key)
        if existing is None or support.evidence_strength > existing.evidence_strength:
            self.supports[key] = support


class GlossaryError(RuntimeError):
    pass


class GlossaryNotFoundError(GlossaryError):
    pass


def _manual_request_entries(meta: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(meta, dict):
        return []
    entries = meta.get("manual_requests")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _latest_manual_request(meta: dict[str, object] | None) -> dict[str, object] | None:
    entries = _manual_request_entries(meta)
    return entries[-1] if entries else None


def _manual_request_entries_for_user(
    meta: dict[str, object] | None,
    *,
    workspace_id: UUID,
    requested_by_user_id: UUID,
) -> list[dict[str, object]]:
    workspace_key = str(workspace_id)
    user_key = str(requested_by_user_id)
    return [
        entry
        for entry in _manual_request_entries(meta)
        if str(entry.get("workspace_id") or "") == workspace_key
        and str(entry.get("requested_by_user_id") or "") == user_key
    ]


def _manual_request_reason(display_term: str, *, has_draft: bool = False, requester_name: str | None = None) -> str:
    requester = requester_name or "구성원"
    if has_draft:
        return f"{display_term} 요청을 바탕으로 작업 초안을 만들었습니다. {requester} 요청 맥락을 검토한 뒤 승인 여부를 결정하세요."
    return f"{display_term}는 {requester} 요청으로 등록된 신규 용어입니다. 초안을 만들고 승인 여부를 검토하세요."


def _parse_request_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _manual_request_list_entry(entry: dict[str, object]) -> GlossaryConceptRequestListEntry:
    return GlossaryConceptRequestListEntry(
        requested_by_name=str(entry.get("requested_by_name") or "").strip() or None,
        requested_by_email=str(entry.get("requested_by_email") or "").strip() or None,
        request_note=str(entry.get("request_note") or "").strip() or None,
        requested_at=_parse_request_datetime(entry.get("requested_at")),
        owner_team_hint=str(entry.get("owner_team_hint") or "").strip() or None,
    )


def normalize_concept_term(value: str) -> str:
    normalized = normalize_whitespace(value).strip()
    normalized = ORDINAL_SUFFIX_PATTERN.sub("", normalized)
    normalized = HEX_SUFFIX_PATTERN.sub("", normalized)
    normalized = normalized.strip(" -_")
    return normalized


def concept_slug(value: str) -> str:
    return slugify(normalize_concept_term(value))


def concept_search_key(value: str | None) -> str:
    if not value:
        return ""
    return normalize_concept_term(value).replace("-", " ").replace("_", " ").lower()


def _is_valid_term(value: str) -> bool:
    stripped = normalize_whitespace(value).strip(' "\ufeff')
    if len(stripped) < 2 or len(stripped) > 80:
        return False
    if not re.search(r"[0-9A-Za-z가-힣]", stripped):
        return False
    if stripped.startswith("-") or stripped.startswith("#"):
        return False
    return True


def is_noise_candidate(value: str) -> bool:
    normalized = normalize_concept_term(value)
    if not normalized:
        return True
    return NOISE_PATTERN.search(normalized) is not None


def classify_concept_type(term: str) -> str:
    if TEAM_PATTERN.search(term):
        return ConceptType.team.value
    if METRIC_PATTERN.search(term):
        return ConceptType.metric.value
    if PROCESS_PATTERN.search(term):
        return ConceptType.process.value
    if PRODUCT_PATTERN.search(term):
        return ConceptType.product.value
    return ConceptType.term.value


def _display_term_for_candidate(candidate: CandidateConcept) -> str:
    most_common = candidate.display_counter.most_common()
    if not most_common:
        return candidate.normalized_term
    top_count = most_common[0][1]
    top_terms = sorted(term for term, count in most_common if count == top_count)
    return top_terms[0]


def _concept_confidence(candidate: CandidateConcept) -> float:
    doc_count = len(candidate.document_ids)
    chunk_count = len(candidate.chunk_ids)
    title_hits = candidate.title_hits
    heading_hits = candidate.evidence_kinds.get("heading", 0)
    table_hits = candidate.evidence_kinds.get("table-field", 0)
    score = (
        min(doc_count, 6) * 0.16
        + min(chunk_count, 10) * 0.03
        + min(title_hits, 4) * 0.12
        + min(heading_hits, 6) * 0.04
        + min(table_hits, 6) * 0.03
        + min(len(candidate.source_systems), 3) * 0.04
    )
    if doc_count == 1 and title_hits >= 1 and not is_noise_candidate(candidate.normalized_term):
        score = max(score, 0.36)
    return round(min(score, 0.99), 4)


def _document_group_key(title: str, slug: str) -> str:
    return concept_search_key(normalize_concept_term(title or slug.replace("-", " ")))


def _heading_terms(section_title: str | None, heading_path: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for raw in [section_title, *heading_path]:
        if raw is None:
            continue
        term = normalize_concept_term(raw)
        key = concept_search_key(term)
        if not term or key in seen or not _is_valid_term(term):
            continue
        seen.add(key)
        values.append(term)
    return values


def _extract_table_terms(content: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    lines = [line.strip() for line in content.splitlines()[:12] if line.strip()]
    if not lines:
        return values
    for line in lines:
        if line.count(",") < 1 and "|" not in line and "\t" not in line:
            continue
        parts = [normalize_concept_term(part.strip(' "\ufeff')) for part in TABLE_SPLIT_PATTERN.split(line) if part.strip()]
        for part in parts[:3]:
            key = concept_search_key(part)
            if not _is_valid_term(part) or key in seen:
                continue
            if len(part.split()) > 4:
                continue
            if re.fullmatch(r"[0-9.]+", part):
                continue
            seen.add(key)
            values.append(part)
    return values[:10]


async def _load_linked_documents(session: AsyncSession, ids: set[UUID]) -> dict[UUID, Document]:
    if not ids:
        return {}
    result = await session.execute(select(Document).where(Document.id.in_(ids)))
    return {document.id: document for document in result.scalars().all()}


def _document_link(document: Document | None) -> GlossaryConceptDocumentLink | None:
    if document is None:
        return None
    return GlossaryConceptDocumentLink(
        id=document.id,
        slug=document.slug,
        title=document.title,
        status=document.status,
        doc_type=document.doc_type,
        owner_team=document.owner_team,
    )


def _validation_run_summary(run: GlossaryValidationRun) -> GlossaryValidationRunSummary:
    return GlossaryValidationRunSummary(
        id=run.id,
        workspace_id=run.workspace_id,
        requested_by_user_id=run.requested_by_user_id,
        mode=run.mode,
        status=run.status,
        target_concept_id=run.target_concept_id,
        source_scope=run.source_scope,
        selected_resource_ids=list(run.selected_resource_ids or []),
        source_sync_summary=dict(run.source_sync_summary or {}),
        validation_summary=dict(run.validation_summary or {}),
        linked_job_ids=list(run.linked_job_ids or []),
        error_message=run.error_message,
        requested_at=run.requested_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        updated_at=run.updated_at,
    )


def _concept_summary(concept: KnowledgeConcept, docs_by_id: dict[UUID, Document]) -> GlossaryConceptSummary:
    canonical_document = docs_by_id.get(concept.canonical_document_id) if concept.canonical_document_id else None
    return GlossaryConceptSummary(
        id=concept.id,
        slug=concept_slug(concept.display_term),
        normalized_term=concept.normalized_term,
        display_term=concept.display_term,
        aliases=list(concept.aliases or []),
        language_code=concept.language_code,
        concept_type=concept.concept_type,
        confidence_score=float(concept.confidence_score),
        support_doc_count=concept.support_doc_count,
        support_chunk_count=concept.support_chunk_count,
        status=concept.status,
        validation_state=concept.validation_state,
        validation_reason=concept.validation_reason,
        last_validated_at=concept.last_validated_at,
        review_required=bool(concept.review_required),
        last_validation_run_id=concept.last_validation_run_id,
        owner_team_hint=concept.owner_team_hint,
        source_system_mix=list(concept.source_system_mix or []),
        generated_document=_document_link(docs_by_id.get(concept.generated_document_id)) if concept.generated_document_id else None,
        canonical_document=_document_link(canonical_document) if canonical_document is not None else None,
        metadata=concept.meta or {},
        refreshed_at=concept.refreshed_at,
        updated_at=concept.updated_at,
        trust=build_concept_trust(
            status=concept.status,
            source_systems=list(concept.source_system_mix or []),
            last_synced_at=concept.refreshed_at,
            evidence_count=concept.support_doc_count,
            source_url=canonical_document.source_url if canonical_document is not None else None,
        ),
    )


async def list_glossary_concepts(
    session: AsyncSession,
    *,
    q: str | None = None,
    status_filter: str | None = None,
    concept_type: str | None = None,
    owner_team: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> GlossaryConceptListResponse:
    filters = []
    if q:
        q_like = f"%{q}%"
        filters.append(
            or_(
                KnowledgeConcept.display_term.ilike(q_like),
                KnowledgeConcept.normalized_term.ilike(q_like),
                func.cast(KnowledgeConcept.aliases, Text).ilike(q_like),
            )
        )
    if status_filter:
        filters.append(KnowledgeConcept.status == status_filter)
    if concept_type:
        filters.append(KnowledgeConcept.concept_type == concept_type)
    if owner_team:
        filters.append(KnowledgeConcept.owner_team_hint == owner_team)

    stmt = (
        select(KnowledgeConcept)
        .where(*filters)
        .order_by(
            KnowledgeConcept.review_required.desc(),
            case(
                (KnowledgeConcept.validation_state == GlossaryValidationState.stale_evidence.value, 0),
                (KnowledgeConcept.validation_state == GlossaryValidationState.missing_draft.value, 1),
                (KnowledgeConcept.validation_state == GlossaryValidationState.needs_update.value, 2),
                (KnowledgeConcept.validation_state == GlossaryValidationState.new_term.value, 3),
                else_=4,
            ).asc(),
            case(
                (KnowledgeConcept.status == ConceptStatus.approved.value, 0),
                (KnowledgeConcept.status == ConceptStatus.drafted.value, 1),
                (KnowledgeConcept.status == ConceptStatus.suggested.value, 2),
                (KnowledgeConcept.status == ConceptStatus.stale.value, 3),
                else_=4,
            ).asc(),
            KnowledgeConcept.confidence_score.desc(),
            KnowledgeConcept.support_doc_count.desc(),
            KnowledgeConcept.updated_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    concepts = list((await session.execute(stmt)).scalars().all())
    total = int((await session.execute(select(func.count(KnowledgeConcept.id)).where(*filters))).scalar_one())
    linked_doc_ids = {
        concept.generated_document_id
        for concept in concepts
        if concept.generated_document_id is not None
    } | {
        concept.canonical_document_id
        for concept in concepts
        if concept.canonical_document_id is not None
    }
    docs_by_id = await _load_linked_documents(session, {doc_id for doc_id in linked_doc_ids if doc_id is not None})
    return GlossaryConceptListResponse(
        items=[_concept_summary(concept, docs_by_id) for concept in concepts],
        total=total,
        limit=limit,
        offset=offset,
    )


async def _get_concept_or_raise(session: AsyncSession, concept_id: UUID) -> KnowledgeConcept:
    concept = await session.get(KnowledgeConcept, concept_id)
    if concept is None:
        raise GlossaryNotFoundError("Glossary concept not found")
    return concept


async def _find_concept_by_exact_term(session: AsyncSession, term: str, aliases: list[str]) -> KnowledgeConcept | None:
    requested_keys = {
        concept_search_key(value)
        for value in [term, *aliases]
        if concept_search_key(value)
    }
    if not requested_keys:
        return None
    concepts = list((await session.execute(select(KnowledgeConcept))).scalars().all())
    for concept in concepts:
        if _concept_terms(concept).intersection(requested_keys):
            return concept
    return None


async def create_glossary_concept_request(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    requested_by_user_id: UUID,
    requested_by_name: str,
    requested_by_email: str,
    payload: GlossaryConceptRequestCreateRequest,
) -> GlossaryConceptRequestResponse:
    raw_display_term = normalize_whitespace(payload.term).strip()
    normalized_term = normalize_concept_term(payload.term)
    if not _is_valid_term(normalized_term):
        raise GlossaryError("A valid glossary term is required.")

    aliases: list[str] = []
    seen_aliases: set[str] = set()
    for value in [raw_display_term, normalized_term, *payload.aliases]:
        alias = normalize_whitespace(value).strip()
        alias_key = concept_search_key(alias)
        if not alias or not alias_key or alias_key in seen_aliases:
            continue
        seen_aliases.add(alias_key)
        aliases.append(alias)

    existing = await _find_concept_by_exact_term(session, normalized_term, aliases)
    if existing is not None and existing.status == ConceptStatus.approved.value:
        docs_by_id = await _load_linked_documents(
            session,
            {doc_id for doc_id in [existing.generated_document_id, existing.canonical_document_id] if doc_id is not None},
        )
        return GlossaryConceptRequestResponse(
            request_status="already_exists",
            message="이미 승인된 핵심 개념입니다.",
            concept=_concept_summary(existing, docs_by_id),
        )

    request_entry = {
        "workspace_id": str(workspace_id),
        "requested_by_user_id": str(requested_by_user_id),
        "requested_by_name": requested_by_name,
        "requested_by_email": requested_by_email,
        "request_note": normalize_whitespace(payload.request_note or "").strip() or None,
        "requested_at": utcnow().isoformat(),
        "owner_team_hint": normalize_whitespace(payload.owner_team_hint or "").strip() or None,
    }

    if existing is not None:
        meta = dict(existing.meta or {})
        entries = _manual_request_entries(meta)
        entries.append(request_entry)
        meta["manual_requests"] = entries[-10:]
        meta["manual_request_count"] = int(meta.get("manual_request_count") or 0) + 1
        meta["manual_request_latest"] = request_entry
        existing.meta = meta
        if request_entry["owner_team_hint"] and not existing.owner_team_hint:
            existing.owner_team_hint = str(request_entry["owner_team_hint"])
        if existing.status in {ConceptStatus.ignored.value, ConceptStatus.stale.value}:
            existing.status = ConceptStatus.suggested.value
        if existing.generated_document_id is None and existing.status != ConceptStatus.approved.value:
            existing.validation_state = GlossaryValidationState.new_term.value
        existing.review_required = True
        existing.validation_reason = _manual_request_reason(
            existing.display_term,
            requester_name=requested_by_name,
        )
        existing.last_validated_at = utcnow()
        existing.updated_at = utcnow()
        existing.refreshed_at = utcnow()
        await session.commit()
        return GlossaryConceptRequestResponse(
            request_status="updated_existing",
            message="이미 등록된 용어 후보에 요청을 추가했습니다. 관리자가 같은 항목에서 검토할 수 있습니다.",
            concept=(await get_glossary_concept_detail(session, existing.id)).concept,
        )

    concept = KnowledgeConcept(
        normalized_term=normalized_term,
        display_term=raw_display_term or normalized_term,
        aliases=aliases,
        language_code="ko",
        concept_type=classify_concept_type(raw_display_term or normalized_term),
        confidence_score=0.0,
        support_doc_count=0,
        support_chunk_count=0,
        status=ConceptStatus.suggested.value,
        validation_state=GlossaryValidationState.new_term.value,
        validation_reason=_manual_request_reason(raw_display_term or normalized_term, requester_name=requested_by_name),
        evidence_signature=None,
        last_validation_run_id=None,
        last_validated_at=utcnow(),
        review_required=True,
        owner_team_hint=normalize_whitespace(payload.owner_team_hint or "").strip() or None,
        source_system_mix=[],
        meta={
            "request_source": "manual_request",
            "manual_request_count": 1,
            "manual_request_latest": request_entry,
            "manual_requests": [request_entry],
        },
        refreshed_at=utcnow(),
    )
    session.add(concept)
    await session.flush()
    await session.commit()
    return GlossaryConceptRequestResponse(
        request_status="created",
        message="새 핵심 개념 요청을 등록했습니다. 관리자가 지식 검수에서 초안을 만들고 승인할 수 있습니다.",
        concept=(await get_glossary_concept_detail(session, concept.id)).concept,
    )


async def list_glossary_concept_requests_for_user(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    requested_by_user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> GlossaryConceptRequestListResponse:
    concepts = list((await session.execute(select(KnowledgeConcept))).scalars().all())
    matched: list[tuple[KnowledgeConcept, list[dict[str, object]], dict[str, object], datetime | None]] = []

    for concept in concepts:
        entries = _manual_request_entries_for_user(
            concept.meta or {},
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
        )
        if not entries:
            continue
        latest_request = entries[-1]
        matched.append((concept, entries, latest_request, _parse_request_datetime(latest_request.get("requested_at"))))

    matched.sort(
        key=lambda row: (
            row[3].timestamp() if row[3] is not None else 0.0,
            row[0].updated_at.timestamp() if row[0].updated_at is not None else 0.0,
        ),
        reverse=True,
    )

    total = len(matched)
    page = matched[offset : offset + limit]
    linked_doc_ids = {
        concept.generated_document_id
        for concept, _, _, _ in page
        if concept.generated_document_id is not None
    } | {
        concept.canonical_document_id
        for concept, _, _, _ in page
        if concept.canonical_document_id is not None
    }
    docs_by_id = await _load_linked_documents(session, {doc_id for doc_id in linked_doc_ids if doc_id is not None})

    return GlossaryConceptRequestListResponse(
        items=[
            GlossaryConceptRequestListItem(
                concept=_concept_summary(concept, docs_by_id),
                latest_request=_manual_request_list_entry(latest_request),
                request_count=len(entries),
            )
            for concept, entries, latest_request, _ in page
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_glossary_concept_detail(session: AsyncSession, concept_id: UUID) -> GlossaryConceptDetailResponse:
    concept = await _get_concept_or_raise(session, concept_id)
    support_rows = (
        await session.execute(
            select(
                ConceptSupport,
                Document,
                Document.slug,
                Document.title,
                Document.status,
                Document.doc_type,
                Document.owner_team,
            )
            .join(Document, Document.id == ConceptSupport.document_id)
            .where(ConceptSupport.concept_id == concept_id)
            .order_by(ConceptSupport.evidence_strength.desc(), ConceptSupport.evidence_kind.asc())
        )
    ).all()
    support_items = [
        GlossarySupportItem(
            id=support.id,
            document_id=support.document_id,
            document_slug=document_slug,
            document_title=document_title,
            document_status=document_status,
            document_doc_type=document_doc_type,
            owner_team=owner_team,
            revision_id=support.revision_id,
            chunk_id=support.chunk_id,
            evidence_kind=support.evidence_kind,
            evidence_term=support.evidence_term,
            evidence_strength=float(support.evidence_strength),
            support_group_key=support.support_group_key,
            support_text=support.support_text,
            metadata=support.meta or {},
            trust=build_document_trust(
                source_system=document.source_system,
                source_url=document.source_url,
                last_synced_at=document.last_ingested_at,
                doc_type=document.doc_type,
            ),
        )
        for support, document, document_slug, document_title, document_status, document_doc_type, owner_team in support_rows
    ]
    related_stmt = (
        select(KnowledgeConcept)
        .where(KnowledgeConcept.id != concept.id, KnowledgeConcept.status != ConceptStatus.ignored.value)
        .order_by(func.similarity(KnowledgeConcept.display_term, concept.display_term).desc(), KnowledgeConcept.confidence_score.desc())
        .limit(6)
    )
    related_concepts = list((await session.execute(related_stmt)).scalars().all())
    linked_ids = {
        doc_id
        for doc_id in [concept.generated_document_id, concept.canonical_document_id, *[item.generated_document_id for item in related_concepts], *[item.canonical_document_id for item in related_concepts]]
        if doc_id is not None
    }
    docs_by_id = await _load_linked_documents(session, linked_ids)
    return GlossaryConceptDetailResponse(
        concept=_concept_summary(concept, docs_by_id),
        supports=support_items,
        related_concepts=[_concept_summary(item, docs_by_id) for item in related_concepts],
    )


async def get_glossary_concept_by_slug(session: AsyncSession, slug: str) -> GlossaryConceptDetailResponse:
    result = await session.execute(select(KnowledgeConcept).where(KnowledgeConcept.status != ConceptStatus.ignored.value))
    concepts = list(result.scalars().all())
    for concept in concepts:
        if concept_slug(concept.display_term) == slug:
            return await get_glossary_concept_detail(session, concept.id)
    raise GlossaryNotFoundError("Glossary concept not found")


async def resolve_concept(session: AsyncSession, query: str) -> KnowledgeConcept | None:
    normalized = normalize_concept_term(query)
    if not normalized:
        return None
    exact_stmt = (
        select(KnowledgeConcept)
        .where(
            KnowledgeConcept.status != ConceptStatus.ignored.value,
            KnowledgeConcept.status != ConceptStatus.stale.value,
            or_(
                KnowledgeConcept.normalized_term == normalized,
                KnowledgeConcept.display_term == normalized,
            ),
        )
        .order_by(
            case(
                (KnowledgeConcept.status == ConceptStatus.approved.value, 0),
                (KnowledgeConcept.status == ConceptStatus.drafted.value, 1),
                else_=2,
            ).asc(),
            KnowledgeConcept.confidence_score.desc(),
        )
        .limit(1)
    )
    concept = (await session.execute(exact_stmt)).scalar_one_or_none()
    if concept is not None:
        return concept

    fuzzy_stmt = (
        select(KnowledgeConcept)
        .where(
            KnowledgeConcept.status != ConceptStatus.ignored.value,
            KnowledgeConcept.status != ConceptStatus.stale.value,
        )
        .order_by(
            func.greatest(
                func.similarity(KnowledgeConcept.display_term, normalized),
                func.similarity(KnowledgeConcept.normalized_term, normalized),
            ).desc(),
            KnowledgeConcept.confidence_score.desc(),
        )
        .limit(25)
    )
    candidates = list((await session.execute(fuzzy_stmt)).scalars().all())
    best: tuple[float, KnowledgeConcept] | None = None
    query_key = concept_search_key(normalized)
    for candidate in candidates:
        candidate_score = max(
            1.0 if concept_search_key(candidate.normalized_term) == query_key else 0.0,
            0.95 if concept_search_key(candidate.display_term) == query_key else 0.0,
            *[
                0.9 if concept_search_key(alias) == query_key else 0.0
                for alias in (candidate.aliases or [])
            ],
        )
        candidate_score = max(
            candidate_score,
            float((candidate.confidence_score or 0) * 0.5)
            + float(max(
                0.0,
                min(1.0, math.fsum(
                    [
                        0.7 if query_key and query_key in concept_search_key(candidate.display_term) else 0.0,
                        0.75 if query_key and query_key in concept_search_key(candidate.normalized_term) else 0.0,
                        max(
                            [
                                0.65 if query_key and query_key in concept_search_key(alias) else 0.0
                                for alias in (candidate.aliases or [])
                            ],
                            default=0.0,
                        ),
                    ]
                )),
            )),
        )
        if best is None or candidate_score > best[0]:
            best = (candidate_score, candidate)
    if best is None or best[0] < 0.45:
        return None
    return best[1]


async def get_concept_support_hits(
    session: AsyncSession,
    concept_id: UUID,
    *,
    limit: int,
    owner_team: str | None = None,
    doc_type: str | None = None,
    source_system: str | None = None,
    include_evidence_only: bool = True,
) -> list[dict[str, object]]:
    filters = [ConceptSupport.concept_id == concept_id]
    if owner_team is not None:
        filters.append(Document.owner_team == owner_team)
    if doc_type is not None:
        filters.append(Document.doc_type == doc_type)
    if source_system is not None:
        filters.append(Document.source_system == source_system)
    if not include_evidence_only:
        filters.append(Document.visibility_scope == DocumentVisibilityScope.member_visible.value)

    stmt = (
        select(
            ConceptSupport.id.label("support_id"),
            ConceptSupport.concept_id,
            ConceptSupport.evidence_kind,
            ConceptSupport.evidence_strength,
            ConceptSupport.support_group_key,
            Document.id.label("document_id"),
            Document.current_revision_id.label("revision_id"),
            Document.title.label("document_title"),
            Document.slug.label("document_slug"),
            Document.source_system,
            Document.source_url,
            Document.last_ingested_at.label("last_synced_at"),
            Document.meta.label("document_metadata"),
            Document.owner_team,
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.section_title,
            DocumentChunk.heading_path,
            DocumentChunk.content_text,
            ConceptSupport.support_text,
        )
        .join(Document, Document.id == ConceptSupport.document_id)
        .outerjoin(DocumentChunk, DocumentChunk.id == ConceptSupport.chunk_id)
        .where(*filters)
        .order_by(ConceptSupport.evidence_strength.desc(), ConceptSupport.evidence_kind.asc(), Document.updated_at.desc())
        .limit(limit * 6)
    )
    rows = (await session.execute(stmt)).mappings().all()

    selected: list[dict[str, object]] = []
    seen_groups: set[str] = set()
    seen_documents: set[UUID] = set()
    for row in rows:
        group_key = str(row["support_group_key"])
        document_id = row["document_id"]
        if group_key not in seen_groups:
            selected.append(dict(row))
            seen_groups.add(group_key)
            seen_documents.add(document_id)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for row in rows:
            document_id = row["document_id"]
            if document_id in seen_documents:
                continue
            selected.append(dict(row))
            seen_documents.add(document_id)
            if len(selected) >= limit:
                break
    return selected[:limit]


def _concept_terms(concept: KnowledgeConcept) -> set[str]:
    return {
        concept_search_key(value)
        for value in [concept.normalized_term, concept.display_term, *(concept.aliases or [])]
        if value
    }


def _candidate_signature(candidate: CandidateConcept) -> str | None:
    if not candidate.supports:
        return None
    parts = [
        "|".join(
            [
                str(support.document_id),
                str(support.chunk_id or ""),
                support.evidence_kind,
                support.evidence_term,
                f"{support.evidence_strength:.3f}",
                support.support_group_key,
            ]
        )
        for support in sorted(
            candidate.supports.values(),
            key=lambda item: (
                item.document_id,
                str(item.chunk_id or ""),
                item.evidence_kind,
                item.evidence_term,
            ),
        )
    ]
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()


async def _load_glossary_corpus_rows(
    session: AsyncSession,
    *,
    document_ids: set[UUID] | None = None,
) -> list[dict[str, object]]:
    filters = [Document.status == "published", Document.source_system != "glossary"]
    if document_ids is not None:
        if not document_ids:
            return []
        filters.append(Document.id.in_(document_ids))
    stmt = (
        select(
            Document.id.label("document_id"),
            Document.current_revision_id.label("revision_id"),
            Document.title.label("document_title"),
            Document.slug.label("document_slug"),
            Document.status.label("document_status"),
            Document.doc_type.label("document_doc_type"),
            Document.owner_team,
            Document.source_system,
            Document.language_code,
            Document.visibility_scope,
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.section_title,
            DocumentChunk.heading_path,
            DocumentChunk.content_text,
        )
        .join(
            DocumentChunk,
            (DocumentChunk.document_id == Document.id) & (DocumentChunk.revision_id == Document.current_revision_id),
        )
        .where(*filters)
        .order_by(Document.id.asc(), DocumentChunk.chunk_index.asc())
    )
    rows = (await session.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]


def _extract_term_keys_from_rows(rows: list[dict[str, object]]) -> set[str]:
    keys: set[str] = set()
    for row in rows:
        document_title = normalize_concept_term(str(row["document_title"]))
        if _is_valid_term(document_title):
            keys.add(concept_search_key(document_title))
        for heading_term in _heading_terms(row.get("section_title"), list(row.get("heading_path") or [])):
            keys.add(concept_search_key(heading_term))
        for table_term in _extract_table_terms(str(row.get("content_text") or "")):
            keys.add(concept_search_key(table_term))
    return {key for key in keys if key}


async def _load_target_term_keys(session: AsyncSession, target_document_ids: set[UUID]) -> set[str]:
    keys = _extract_term_keys_from_rows(await _load_glossary_corpus_rows(session, document_ids=target_document_ids))
    linked_concepts = list(
        (
            await session.execute(
                select(KnowledgeConcept)
                .join(ConceptSupport, ConceptSupport.concept_id == KnowledgeConcept.id)
                .where(ConceptSupport.document_id.in_(target_document_ids))
            )
        ).scalars().all()
    )
    for concept in linked_concepts:
        keys.update(_concept_terms(concept))
    return {key for key in keys if key}


def _build_candidates(
    rows: list[dict[str, object]],
    *,
    allowed_term_keys: set[str] | None = None,
) -> dict[str, CandidateConcept]:
    candidates: dict[str, CandidateConcept] = {}

    def ensure_candidate(term: str) -> CandidateConcept | None:
        normalized_term = normalize_concept_term(term)
        search_key = concept_search_key(normalized_term)
        if allowed_term_keys is not None and search_key not in allowed_term_keys:
            return None
        candidate = candidates.get(normalized_term)
        if candidate is None:
            candidate = CandidateConcept(normalized_term=normalized_term)
            candidates[normalized_term] = candidate
        return candidate

    for row in rows:
        document_id = row["document_id"]
        revision_id = row["revision_id"]
        chunk_id = row["chunk_id"]
        document_title = str(row["document_title"])
        document_slug = str(row["document_slug"])
        document_status = str(row["document_status"])
        document_doc_type = str(row["document_doc_type"])
        owner_team = row["owner_team"]
        source_system = str(row["source_system"])
        group_key = _document_group_key(document_title, document_slug)

        title_term = normalize_concept_term(document_title)
        if _is_valid_term(title_term):
            candidate = ensure_candidate(title_term)
            if candidate is not None:
                candidate.add_support(
                    display_term=title_term,
                    source_system=source_system,
                    support=CandidateSupport(
                        document_id=document_id,
                        revision_id=revision_id,
                        chunk_id=chunk_id,
                        document_slug=document_slug,
                        document_title=document_title,
                        document_status=document_status,
                        document_doc_type=document_doc_type,
                        owner_team=owner_team,
                        support_group_key=group_key,
                        evidence_kind="title",
                        evidence_term=title_term,
                        support_text=document_title,
                        evidence_strength=3.6,
                    ),
                )

        for heading_term in _heading_terms(row.get("section_title"), list(row.get("heading_path") or [])):
            if concept_search_key(heading_term) == concept_search_key(title_term):
                continue
            candidate = ensure_candidate(heading_term)
            if candidate is None:
                continue
            candidate.add_support(
                display_term=heading_term,
                source_system=source_system,
                support=CandidateSupport(
                    document_id=document_id,
                    revision_id=revision_id,
                    chunk_id=chunk_id,
                    document_slug=document_slug,
                    document_title=document_title,
                    document_status=document_status,
                    document_doc_type=document_doc_type,
                    owner_team=owner_team,
                    support_group_key=group_key,
                    evidence_kind="heading",
                    evidence_term=heading_term,
                    support_text=heading_term,
                    evidence_strength=2.0,
                ),
            )

        for table_term in _extract_table_terms(str(row.get("content_text") or "")):
            candidate = ensure_candidate(table_term)
            if candidate is None:
                continue
            candidate.add_support(
                display_term=table_term,
                source_system=source_system,
                support=CandidateSupport(
                    document_id=document_id,
                    revision_id=revision_id,
                    chunk_id=chunk_id,
                    document_slug=document_slug,
                    document_title=document_title,
                    document_status=document_status,
                    document_doc_type=document_doc_type,
                    owner_team=owner_team,
                    support_group_key=group_key,
                    evidence_kind="table-field",
                    evidence_term=table_term,
                    support_text=normalize_whitespace(str(row.get("content_text") or ""))[:240],
                    evidence_strength=1.4,
                ),
            )
    return candidates


def _validation_reason(
    *,
    state: str,
    display_term: str,
) -> str:
    if state == GlossaryValidationState.ok.value:
        return f"{display_term} 정의가 최신 근거와 일치합니다."
    if state == GlossaryValidationState.stale_evidence.value:
        return f"{display_term}의 근거 문서가 바뀌었습니다. 현재 승인 문서는 유지하되 다시 검토해야 합니다."
    if state == GlossaryValidationState.missing_draft.value:
        return f"{display_term}는 근거는 충분하지만 작업 초안이 아직 없습니다."
    if state == GlossaryValidationState.needs_update.value:
        return f"{display_term}의 근거가 바뀌어 작업 초안을 갱신해야 합니다."
    return f"{display_term}는 새로 발견된 용어 후보입니다."


async def _apply_glossary_refresh(
    session: AsyncSession,
    *,
    mode: str,
    target_document_ids: set[UUID] | None = None,
    target_concept_id: UUID | None = None,
    validation_run_id: UUID | None = None,
    create_drafts_for_review: bool = False,
) -> dict[str, object]:
    if mode == GlossaryJobScope.incremental.value and not target_document_ids:
        return {
            "updated_concepts": 0,
            "validated_concepts": 0,
            "created_drafts": 0,
            "review_required_count": 0,
            "validation_counts": {},
            "target_document_count": 0,
        }

    allowed_term_keys: set[str] | None = None
    if mode == GlossaryJobScope.incremental.value:
        allowed_term_keys = await _load_target_term_keys(session, target_document_ids or set())
        if not allowed_term_keys:
            return {
                "updated_concepts": 0,
                "validated_concepts": 0,
                "created_drafts": 0,
                "review_required_count": 0,
                "validation_counts": {},
                "target_document_count": len(target_document_ids or set()),
            }
    elif mode == GlossaryJobScope.term.value:
        if target_concept_id is None:
            raise GlossaryError("target_concept_id is required for term validation.")
        target_concept = await _get_concept_or_raise(session, target_concept_id)
        allowed_term_keys = _concept_terms(target_concept)

    rows = await _load_glossary_corpus_rows(session)
    candidates = _build_candidates(rows, allowed_term_keys=allowed_term_keys)
    existing_concepts = {
        concept.normalized_term: concept
        for concept in (await session.execute(select(KnowledgeConcept))).scalars().all()
    }
    targeted_keys = allowed_term_keys or {
        concept_search_key(term)
        for term in {*(candidates.keys()), *existing_concepts.keys()}
        if term
    }
    validation_counts: Counter[str] = Counter()
    updated_concept_ids: list[UUID] = []
    draft_concept_ids: list[UUID] = []

    for normalized_term, candidate in candidates.items():
        display_term = _display_term_for_candidate(candidate)
        support_doc_count = len(candidate.document_ids)
        support_chunk_count = len(candidate.chunk_ids)
        auto_ignored = is_noise_candidate(display_term) and support_doc_count < 2
        keep_candidate = support_doc_count >= 2 or (candidate.title_hits >= 1 and not is_noise_candidate(display_term))
        if not keep_candidate and not auto_ignored:
            continue

        concept = existing_concepts.get(normalized_term)
        next_status = ConceptStatus.ignored.value if auto_ignored else ConceptStatus.suggested.value
        previous_signature = concept.evidence_signature if concept is not None else None
        signature = _candidate_signature(candidate)
        drifted = previous_signature is not None and signature is not None and previous_signature != signature
        is_new = concept is None

        if concept is None:
            concept = KnowledgeConcept(
                normalized_term=normalized_term,
                display_term=display_term,
                aliases=sorted(candidate.aliases),
                language_code="ko",
                concept_type=classify_concept_type(display_term),
                confidence_score=_concept_confidence(candidate),
                support_doc_count=support_doc_count,
                support_chunk_count=support_chunk_count,
                status=next_status,
                validation_state=GlossaryValidationState.new_term.value,
                validation_reason=_validation_reason(
                    state=GlossaryValidationState.new_term.value,
                    display_term=display_term,
                ),
                evidence_signature=signature,
                last_validation_run_id=validation_run_id,
                last_validated_at=utcnow(),
                review_required=True,
                owner_team_hint=candidate.owner_teams.most_common(1)[0][0] if candidate.owner_teams else None,
                source_system_mix=sorted(candidate.source_systems),
                meta={"auto_ignored": auto_ignored},
                refreshed_at=utcnow(),
            )
            session.add(concept)
            await session.flush()
        else:
            concept.display_term = display_term
            concept.aliases = sorted(candidate.aliases)
            concept.language_code = "ko"
            concept.concept_type = classify_concept_type(display_term)
            concept.confidence_score = _concept_confidence(candidate)
            concept.support_doc_count = support_doc_count
            concept.support_chunk_count = support_chunk_count
            concept.owner_team_hint = candidate.owner_teams.most_common(1)[0][0] if candidate.owner_teams else None
            concept.source_system_mix = sorted(candidate.source_systems)
            concept.meta = {**(concept.meta or {}), "auto_ignored": auto_ignored}
            concept.refreshed_at = utcnow()
            if concept.status not in {ConceptStatus.approved.value, ConceptStatus.drafted.value, ConceptStatus.ignored.value}:
                concept.status = next_status
            elif auto_ignored and concept.status == ConceptStatus.suggested.value:
                concept.status = ConceptStatus.ignored.value
            if concept.generated_document_id and concept.status == ConceptStatus.suggested.value:
                concept.status = ConceptStatus.drafted.value
            if concept.canonical_document_id:
                concept.status = ConceptStatus.approved.value

            if concept.status == ConceptStatus.ignored.value:
                concept.validation_state = GlossaryValidationState.ok.value
                concept.review_required = False
            elif concept.status == ConceptStatus.approved.value:
                concept.validation_state = (
                    GlossaryValidationState.stale_evidence.value if drifted else GlossaryValidationState.ok.value
                )
                concept.review_required = drifted
            elif is_new:
                concept.validation_state = GlossaryValidationState.new_term.value
                concept.review_required = True
            elif concept.generated_document_id is None:
                concept.validation_state = GlossaryValidationState.missing_draft.value
                concept.review_required = True
            else:
                concept.validation_state = GlossaryValidationState.needs_update.value
                concept.review_required = True

            concept.validation_reason = _validation_reason(
                state=concept.validation_state,
                display_term=display_term,
            )
            concept.evidence_signature = signature
            concept.last_validation_run_id = validation_run_id
            concept.last_validated_at = utcnow()
            await session.flush()

        updated_concept_ids.append(concept.id)
        validation_counts[concept.validation_state] += 1
        if create_drafts_for_review and concept.review_required and concept.status == ConceptStatus.approved.value:
            draft_concept_ids.append(concept.id)
        await session.execute(delete(ConceptSupport).where(ConceptSupport.concept_id == concept.id))

        supports = sorted(candidate.supports.values(), key=lambda item: item.evidence_strength, reverse=True)[:48]
        for support in supports:
            session.add(
                ConceptSupport(
                    concept_id=concept.id,
                    document_id=support.document_id,
                    revision_id=support.revision_id,
                    chunk_id=support.chunk_id,
                    support_group_key=support.support_group_key,
                    evidence_kind=support.evidence_kind,
                    evidence_term=support.evidence_term,
                    support_text=support.support_text,
                    evidence_strength=support.evidence_strength,
                    meta=support.metadata,
                )
            )

    active_keys = {
        concept_search_key(normalized_term)
        for normalized_term, candidate in candidates.items()
        if len(candidate.document_ids) >= 1
    }
    for concept in existing_concepts.values():
        concept_keys = _concept_terms(concept)
        if not concept_keys.intersection(targeted_keys):
            continue
        if concept.normalized_term in candidates or concept_keys.intersection(active_keys):
            continue
        if concept.status == ConceptStatus.ignored.value:
            continue
        concept.status = ConceptStatus.stale.value
        concept.validation_state = GlossaryValidationState.stale_evidence.value
        concept.validation_reason = _validation_reason(
            state=GlossaryValidationState.stale_evidence.value,
            display_term=concept.display_term,
        )
        concept.last_validation_run_id = validation_run_id
        concept.last_validated_at = utcnow()
        concept.review_required = True
        concept.refreshed_at = utcnow()
        updated_concept_ids.append(concept.id)
        validation_counts[concept.validation_state] += 1
        if create_drafts_for_review and concept.canonical_document_id is not None:
            draft_concept_ids.append(concept.id)

    await session.flush()

    created_drafts = 0
    if create_drafts_for_review:
        for concept_id in list(dict.fromkeys(draft_concept_ids)):
            try:
                await create_or_regenerate_glossary_draft(
                    session,
                    concept_id,
                    GlossaryDraftRequest(regenerate=True),
                    commit=False,
                )
                created_drafts += 1
            except GlossaryError:
                continue

    review_required_count = int(
        (
            await session.execute(
                select(func.count(KnowledgeConcept.id)).where(KnowledgeConcept.review_required.is_(True))
            )
        ).scalar_one()
    )
    await session.flush()
    return {
        "updated_concepts": len(updated_concept_ids),
        "validated_concepts": sum(validation_counts.values()),
        "created_drafts": created_drafts,
        "review_required_count": review_required_count,
        "validation_counts": dict(validation_counts),
        "target_document_count": len(target_document_ids or set()),
    }


async def refresh_glossary_concepts(
    session: AsyncSession,
    *,
    scope: str = GlossaryJobScope.full.value,
    target_document_id: UUID | None = None,
) -> int:
    summary = await _apply_glossary_refresh(
        session,
        mode=GlossaryJobScope.incremental.value if scope == GlossaryJobScope.incremental.value else GlossaryJobScope.full.value,
        target_document_ids={target_document_id} if target_document_id is not None else None,
        create_drafts_for_review=False,
    )
    return int(summary["updated_concepts"])


async def update_glossary_concept(
    session: AsyncSession,
    concept_id: UUID,
    payload: GlossaryConceptUpdateRequest,
) -> GlossaryConceptDetailResponse:
    concept = await _get_concept_or_raise(session, concept_id)

    if payload.action == "approve":
        previous_canonical_document_id = concept.canonical_document_id
        canonical_document_id = payload.canonical_document_id or concept.canonical_document_id or concept.generated_document_id
        if canonical_document_id is None:
            raise GlossaryError("A canonical glossary document is required before approval.")
        canonical_document = await session.get(Document, canonical_document_id)
        if canonical_document is None:
            raise GlossaryError("Canonical glossary document not found.")
        target_slug = f"glossary-{concept_slug(concept.display_term)}"
        slug_owner = (
            await session.execute(
                select(Document).where(Document.slug == target_slug, Document.id != canonical_document.id)
            )
        ).scalar_one_or_none()
        if slug_owner is not None:
            slug_owner.slug = f"{target_slug}-{str(slug_owner.id).split('-')[0]}"
            if slug_owner.source_system == "glossary":
                slug_owner.status = "archived"
            slug_owner.updated_at = utcnow()
        if previous_canonical_document_id is not None and previous_canonical_document_id != canonical_document.id:
            previous_canonical = await session.get(Document, previous_canonical_document_id)
            if previous_canonical is not None and previous_canonical.source_system == "glossary":
                previous_canonical.status = "archived"
                previous_canonical.updated_at = utcnow()
        canonical_document.slug = target_slug
        canonical_document.doc_type = "glossary"
        canonical_document.status = "published"
        if concept.owner_team_hint and not canonical_document.owner_team:
            canonical_document.owner_team = concept.owner_team_hint
        canonical_document.updated_at = utcnow()
        concept.status = ConceptStatus.approved.value
        concept.canonical_document_id = canonical_document.id
        if concept.generated_document_id == canonical_document.id:
            concept.generated_document_id = None
    elif payload.action == "ignore":
        concept.status = ConceptStatus.ignored.value
    elif payload.action == "mark_stale":
        concept.status = ConceptStatus.stale.value
    elif payload.action == "suggest":
        concept.status = ConceptStatus.suggested.value
    elif payload.action == "merge":
        if payload.merge_into_concept_id is None:
            raise GlossaryError("merge_into_concept_id is required for merge")
        target = await _get_concept_or_raise(session, payload.merge_into_concept_id)
        supports = (
            await session.execute(
                select(ConceptSupport).where(ConceptSupport.concept_id.in_([concept.id, target.id]))
            )
        ).scalars().all()
        target.aliases = sorted({*(target.aliases or []), *(concept.aliases or []), concept.display_term})
        if target.generated_document_id is None:
            target.generated_document_id = concept.generated_document_id
        if target.canonical_document_id is None:
            target.canonical_document_id = concept.canonical_document_id
        await session.execute(
            delete(ConceptSupport).where(ConceptSupport.concept_id == target.id)
        )
        seen_supports: set[tuple[UUID, UUID | None, str, str]] = set()
        for support in supports:
            key = (support.document_id, support.chunk_id, support.evidence_kind, support.evidence_term)
            if key in seen_supports:
                continue
            seen_supports.add(key)
            session.add(
                ConceptSupport(
                    concept_id=target.id,
                    document_id=support.document_id,
                    revision_id=support.revision_id,
                    chunk_id=support.chunk_id,
                    support_group_key=support.support_group_key,
                    evidence_kind=support.evidence_kind,
                    evidence_term=support.evidence_term,
                    support_text=support.support_text,
                    evidence_strength=support.evidence_strength,
                    meta=support.meta,
                )
            )
        concept.status = ConceptStatus.ignored.value
        concept.meta = {**(concept.meta or {}), "merged_into": str(target.id)}
    elif payload.action == "split":
        if not payload.split_aliases:
            raise GlossaryError("split_aliases is required for split")
        remaining_aliases = {alias for alias in (concept.aliases or []) if alias not in payload.split_aliases}
        concept.aliases = sorted(remaining_aliases)
        supports = (
            await session.execute(select(ConceptSupport).where(ConceptSupport.concept_id == concept.id))
        ).scalars().all()
        for alias in payload.split_aliases:
            normalized_alias = normalize_concept_term(alias)
            split_concept = KnowledgeConcept(
                normalized_term=normalized_alias,
                display_term=alias,
                aliases=[alias],
                language_code=concept.language_code,
                concept_type=classify_concept_type(alias),
                confidence_score=max(0.25, float(concept.confidence_score) * 0.75),
                support_doc_count=0,
                support_chunk_count=0,
                status=ConceptStatus.suggested.value,
                owner_team_hint=concept.owner_team_hint,
                source_system_mix=list(concept.source_system_mix or []),
                meta={"split_from": str(concept.id)},
                refreshed_at=utcnow(),
            )
            session.add(split_concept)
            await session.flush()
            matching_supports = [
                support
                for support in supports
                if concept_search_key(alias) in concept_search_key(support.evidence_term)
                or concept_search_key(alias) in concept_search_key(support.support_text)
            ]
            split_concept.support_doc_count = len({item.document_id for item in matching_supports})
            split_concept.support_chunk_count = len({item.chunk_id for item in matching_supports if item.chunk_id is not None})
            for support in matching_supports:
                session.add(
                    ConceptSupport(
                        concept_id=split_concept.id,
                        document_id=support.document_id,
                        revision_id=support.revision_id,
                        chunk_id=support.chunk_id,
                        support_group_key=support.support_group_key,
                        evidence_kind=support.evidence_kind,
                        evidence_term=support.evidence_term,
                        support_text=support.support_text,
                        evidence_strength=max(float(support.evidence_strength) * 0.8, 0.6),
                        meta={**(support.meta or {}), "split_from": str(concept.id)},
                    )
                )
    else:
        raise GlossaryError(f"Unsupported glossary action: {payload.action}")

    if concept.status == ConceptStatus.approved.value:
        concept.validation_state = GlossaryValidationState.ok.value
        concept.review_required = False
    elif concept.status == ConceptStatus.ignored.value:
        concept.validation_state = GlossaryValidationState.ok.value
        concept.review_required = False
    elif concept.status == ConceptStatus.stale.value:
        concept.validation_state = GlossaryValidationState.stale_evidence.value
        concept.review_required = True
    elif concept.generated_document_id is None:
        concept.validation_state = GlossaryValidationState.missing_draft.value
        concept.review_required = True
    else:
        concept.validation_state = GlossaryValidationState.needs_update.value
        concept.review_required = True
    concept.validation_reason = _validation_reason(
        state=concept.validation_state,
        display_term=concept.display_term,
    )
    concept.last_validated_at = utcnow()
    concept.updated_at = utcnow()
    concept.refreshed_at = utcnow()
    await session.commit()
    return await get_glossary_concept_detail(session, concept.id)


async def create_or_regenerate_glossary_draft(
    session: AsyncSession,
    concept_id: UUID,
    payload: GlossaryDraftRequest,
    *,
    commit: bool = True,
) -> GlossaryConceptDetailResponse:
    concept = await _get_concept_or_raise(session, concept_id)
    if concept.generated_document_id is not None and not payload.regenerate:
        return await get_glossary_concept_detail(session, concept.id)
    from app.schemas.documents import IngestDocumentRequest
    from app.services.document_drafts import generate_definition_markdown_from_references
    from app.services.ingest import ingest_document

    support_hits = await get_concept_support_hits(session, concept.id, limit=8)
    manual_request = _latest_manual_request(concept.meta or {})
    if support_hits:
        markdown, references = await generate_definition_markdown_from_references(
            topic=concept.display_term,
            domain=payload.domain,
            support_rows=support_hits,
            allow_fallback=True,
        )
    elif manual_request is not None:
        aliases = ", ".join(list(concept.aliases or [])[:6]) or "없음"
        request_note = str(manual_request.get("request_note") or "").strip()
        requester_name = str(manual_request.get("requested_by_name") or "구성원")
        requester_email = str(manual_request.get("requested_by_email") or "").strip()
        requested_at = str(manual_request.get("requested_at") or "")
        requested_at_line = f"- Requested at: {requested_at}" if requested_at else None
        requester_line = f"- Requested by: {requester_name} ({requester_email})" if requester_email else f"- Requested by: {requester_name}"
        domain_label = payload.domain or concept.owner_team_hint or "General"
        request_note_block = request_note or "No additional request note was provided."
        markdown = "\n".join(
            [
                f"# {concept.display_term}",
                "",
                f"## Definition",
                f"{concept.display_term} is a requested glossary concept for the {domain_label} domain. Update this draft with the canonical definition before approval.",
                "",
                "## How This Term Is Used Here",
                request_note_block,
                "",
                "## Supporting Details",
                "This draft was created from a manual glossary request and currently has no synced supporting evidence. Add references or supporting links before approval when available.",
                "",
                "## Request Context",
                requester_line,
                *( [requested_at_line] if requested_at_line else [] ),
                f"- Aliases: {aliases}",
                "",
                "## Review Notes",
                "- Confirm the term is valid for the current workspace.",
                "- Refine the definition and examples.",
                "- Link supporting documents once they are available.",
            ]
        )
        references = []
    else:
        raise GlossaryError("No supporting evidence is available for this concept.")

    draft_slug = f"glossary-{concept_slug(concept.display_term)}"
    draft_source_external_id = f"concept:{concept.id}:draft"
    if concept.status == ConceptStatus.approved.value and concept.canonical_document_id is not None:
        draft_slug = f"{draft_slug}-draft"
        draft_source_external_id = f"concept:{concept.id}:draft-working"

    ingest_payload = IngestDocumentRequest(
        source_system="glossary",
        source_external_id=draft_source_external_id,
        source_url=f"glossary://concept/{concept.id}",
        slug=draft_slug,
        title=concept.display_term,
        content_type="markdown",
        content=markdown,
        doc_type="glossary",
        language_code=concept.language_code,
        owner_team=concept.owner_team_hint,
        status="draft",
        priority=40,
        allow_slug_update=True,
        metadata={
            "concept_id": str(concept.id),
            "concept_aliases": list(concept.aliases or []),
            "reference_count": len(references),
        },
    )
    result = await ingest_document(session, ingest_payload)
    concept.generated_document_id = result.document.id
    if concept.status != ConceptStatus.approved.value:
        concept.status = ConceptStatus.drafted.value
        concept.validation_state = GlossaryValidationState.needs_update.value
        concept.review_required = True
        concept.validation_reason = (
            _manual_request_reason(
                concept.display_term,
                has_draft=True,
                requester_name=str(manual_request.get("requested_by_name") or "구성원") if manual_request is not None else None,
            )
            if manual_request is not None and not support_hits
            else _validation_reason(
                state=GlossaryValidationState.needs_update.value,
                display_term=concept.display_term,
            )
        )
    if concept.status == ConceptStatus.approved.value:
        concept.validation_state = GlossaryValidationState.stale_evidence.value
        concept.review_required = True
        concept.validation_reason = _validation_reason(
            state=GlossaryValidationState.stale_evidence.value,
            display_term=concept.display_term,
        )
    concept.last_validated_at = utcnow()
    concept.updated_at = utcnow()
    concept.refreshed_at = utcnow()
    if commit:
        await session.commit()
    else:
        await session.flush()
    return await get_glossary_concept_detail(session, concept.id)


async def enqueue_glossary_refresh_job(
    session: AsyncSession,
    *,
    scope: str = GlossaryJobScope.full.value,
    target_document_id: UUID | None = None,
    priority: int = 200,
) -> GlossaryJob:
    existing = (
        await session.execute(
            select(GlossaryJob)
            .where(
                GlossaryJob.kind == GlossaryJobKind.refresh.value,
                GlossaryJob.status.in_([JobStatus.queued.value, JobStatus.processing.value]),
            )
            .order_by(GlossaryJob.requested_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    job = GlossaryJob(
        kind=GlossaryJobKind.refresh.value,
        scope=scope,
        status=JobStatus.queued.value,
        target_document_id=target_document_id,
        priority=priority,
        attempt_count=0,
        payload={"scope": scope},
        requested_at=utcnow(),
    )
    session.add(job)
    await session.flush()
    return job


async def create_glossary_validation_run(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    requested_by_user_id: UUID | None,
    payload: GlossaryValidationRunCreateRequest,
) -> GlossaryValidationRunSummary:
    if payload.mode == "validate_term" and payload.target_concept_id is None:
        raise GlossaryError("target_concept_id is required for term validation.")
    from app.services.connectors import enqueue_connector_sync_job, _resource_supports_connector_sync

    resource_stmt = (
        select(ConnectorResource)
        .join(ConnectorConnection, ConnectorConnection.id == ConnectorResource.connection_id)
        .where(
            ConnectorConnection.workspace_id == workspace_id,
            ConnectorConnection.owner_scope == ConnectorOwnerScope.workspace.value,
            ConnectorResource.status == ConnectorResourceStatus.active.value,
        )
    )
    if payload.connector_resource_ids:
        resource_stmt = resource_stmt.where(ConnectorResource.id.in_(payload.connector_resource_ids))
    resources = list((await session.execute(resource_stmt)).scalars().all())
    syncable_resources = [resource for resource in resources if _resource_supports_connector_sync(resource)]
    snapshot_resources = [resource for resource in resources if not _resource_supports_connector_sync(resource)]

    run = GlossaryValidationRun(
        workspace_id=workspace_id,
        requested_by_user_id=requested_by_user_id,
        mode=payload.mode,
        status=JobStatus.queued.value,
        target_concept_id=payload.target_concept_id,
        source_scope="selected_resources" if payload.connector_resource_ids else "workspace_active",
        selected_resource_ids=[str(resource.id) for resource in resources],
        source_sync_summary={
            "selected_resource_count": len(resources),
            "sync_requested": payload.mode != "validate_term",
            "queued_sync_resource_count": 0,
            "snapshot_resource_count": len(snapshot_resources),
            "skipped_sync_resource_count": len(snapshot_resources),
        },
        validation_summary={},
        linked_job_ids=[],
        requested_at=utcnow(),
    )
    session.add(run)
    await session.flush()

    linked_job_ids: list[str] = []
    if payload.mode != "validate_term":
        for resource in syncable_resources:
            sync_job = await enqueue_connector_sync_job(
                session,
                resource.connection_id,
                resource.id,
                sync_mode=resource.sync_mode,
                priority=70,
            )
            linked_job_ids.append(str(sync_job.id))
        run.source_sync_summary = {
            **(run.source_sync_summary or {}),
            "queued_sync_resource_count": len(syncable_resources),
        }

    glossary_job = GlossaryJob(
        kind=GlossaryJobKind.validation_run.value,
        scope=(
            GlossaryJobScope.term.value
            if payload.mode == "validate_term"
            else GlossaryJobScope.incremental.value
            if payload.mode == "sync_validate_impacted"
            else GlossaryJobScope.full.value
        ),
        status=JobStatus.queued.value,
        target_concept_id=payload.target_concept_id,
        priority=140,
        attempt_count=0,
        payload={"run_id": str(run.id)},
        requested_at=utcnow(),
    )
    session.add(glossary_job)
    await session.flush()
    linked_job_ids.append(str(glossary_job.id))
    run.linked_job_ids = linked_job_ids
    await session.commit()
    await session.refresh(run)
    return _validation_run_summary(run)


async def list_glossary_validation_runs(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    limit: int = 20,
) -> GlossaryValidationRunListResponse:
    runs = list(
        (
            await session.execute(
                select(GlossaryValidationRun)
                .where(GlossaryValidationRun.workspace_id == workspace_id)
                .order_by(GlossaryValidationRun.requested_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    )
    return GlossaryValidationRunListResponse(items=[_validation_run_summary(run) for run in runs])


async def get_glossary_validation_run(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    run_id: UUID,
) -> GlossaryValidationRunSummary:
    run = await session.get(GlossaryValidationRun, run_id)
    if run is None or run.workspace_id != workspace_id:
        raise GlossaryNotFoundError("Glossary validation run not found.")
    return _validation_run_summary(run)


async def execute_glossary_validation_run(session: AsyncSession, run_id: UUID) -> GlossaryValidationRunSummary:
    run = await session.get(GlossaryValidationRun, run_id)
    if run is None:
        raise GlossaryNotFoundError("Glossary validation run not found.")

    run.status = JobStatus.processing.value
    run.started_at = utcnow()
    run.updated_at = utcnow()
    await session.flush()

    try:
        from app.services.connectors import _resource_supports_connector_sync

        selected_resource_ids = [UUID(value) for value in (run.selected_resource_ids or [])]
        target_document_ids: set[UUID] = set()
        source_sync_summary = dict(run.source_sync_summary or {})
        if run.mode != "validate_term" and selected_resource_ids:
            selected_resources = list(
                (
                    await session.execute(select(ConnectorResource).where(ConnectorResource.id.in_(selected_resource_ids)))
                ).scalars().all()
            )
            syncable_resource_ids = [
                resource.id for resource in selected_resources if _resource_supports_connector_sync(resource)
            ]
            snapshot_resource_ids = [
                resource.id for resource in selected_resources if not _resource_supports_connector_sync(resource)
            ]
            touched_items = list(
                (
                    await session.execute(
                        select(ConnectorSourceItem)
                        .where(
                            ConnectorSourceItem.resource_id.in_(syncable_resource_ids or selected_resource_ids),
                            ConnectorSourceItem.last_synced_at >= run.requested_at,
                            ConnectorSourceItem.internal_document_id.is_not(None),
                        )
                    )
                ).scalars().all()
            )
            target_document_ids = {
                item.internal_document_id
                for item in touched_items
                if item.internal_document_id is not None
            }
            snapshot_document_ids: set[UUID] = set()
            if run.mode == "sync_validate_impacted" and snapshot_resource_ids:
                snapshot_items = list(
                    (
                        await session.execute(
                            select(ConnectorSourceItem)
                            .where(
                                ConnectorSourceItem.resource_id.in_(snapshot_resource_ids),
                                ConnectorSourceItem.internal_document_id.is_not(None),
                                ConnectorSourceItem.item_status.in_(
                                    [
                                        ConnectorSourceItemStatus.imported.value,
                                        ConnectorSourceItemStatus.unchanged.value,
                                        ConnectorSourceItemStatus.failed.value,
                                        ConnectorSourceItemStatus.unsupported.value,
                                    ]
                                ),
                            )
                        )
                    ).scalars().all()
                )
                snapshot_document_ids = {
                    item.internal_document_id
                    for item in snapshot_items
                    if item.internal_document_id is not None
                }
                target_document_ids.update(snapshot_document_ids)
            source_sync_summary = {
                **source_sync_summary,
                "touched_source_item_count": len(touched_items),
                "touched_document_count": len(target_document_ids),
                "snapshot_document_count": len(snapshot_document_ids),
            }

        validation_summary = await _apply_glossary_refresh(
            session,
            mode=(
                GlossaryJobScope.term.value
                if run.mode == "validate_term"
                else GlossaryJobScope.incremental.value
                if run.mode == "sync_validate_impacted"
                else GlossaryJobScope.full.value
            ),
            target_document_ids=target_document_ids or None,
            target_concept_id=run.target_concept_id,
            validation_run_id=run.id,
            create_drafts_for_review=True,
        )
        run.source_sync_summary = source_sync_summary
        run.validation_summary = dict(validation_summary)
        run.status = JobStatus.completed.value
        run.error_message = None
        run.finished_at = utcnow()
        await session.flush()
        return _validation_run_summary(run)
    except Exception as exc:  # noqa: BLE001
        run.status = JobStatus.failed.value
        run.error_message = str(exc)
        run.finished_at = utcnow()
        await session.flush()
        raise
