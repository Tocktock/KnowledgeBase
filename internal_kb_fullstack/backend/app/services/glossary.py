from __future__ import annotations

import math
import re
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
    Document,
    DocumentChunk,
    GlossaryJob,
    GlossaryJobKind,
    GlossaryJobScope,
    JobStatus,
    KnowledgeConcept,
)
from app.schemas.glossary import (
    GlossaryConceptDetailResponse,
    GlossaryConceptDocumentLink,
    GlossaryConceptListResponse,
    GlossaryConceptSummary,
    GlossaryConceptUpdateRequest,
    GlossaryDraftRequest,
    GlossarySupportItem,
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
) -> list[dict[str, object]]:
    filters = [ConceptSupport.concept_id == concept_id]
    if owner_team is not None:
        filters.append(Document.owner_team == owner_team)
    if doc_type is not None:
        filters.append(Document.doc_type == doc_type)
    if source_system is not None:
        filters.append(Document.source_system == source_system)

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


async def refresh_glossary_concepts(session: AsyncSession) -> int:
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
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.section_title,
            DocumentChunk.heading_path,
            DocumentChunk.content_text,
        )
        .join(DocumentChunk, (DocumentChunk.document_id == Document.id) & (DocumentChunk.revision_id == Document.current_revision_id))
        .where(Document.status == "published", Document.source_system != "glossary")
        .order_by(Document.id.asc(), DocumentChunk.chunk_index.asc())
    )
    rows = (await session.execute(stmt)).mappings().all()

    candidates: dict[str, CandidateConcept] = {}

    def ensure_candidate(term: str) -> CandidateConcept:
        normalized_term = normalize_concept_term(term)
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

        for heading_term in _heading_terms(row["section_title"], list(row["heading_path"] or [])):
            if concept_search_key(heading_term) == concept_search_key(title_term):
                continue
            candidate = ensure_candidate(heading_term)
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

        for table_term in _extract_table_terms(str(row["content_text"])):
            candidate = ensure_candidate(table_term)
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
                    support_text=normalize_whitespace(str(row["content_text"]))[:240],
                    evidence_strength=1.4,
                ),
            )

    existing_concepts = {
        concept.normalized_term: concept
        for concept in (await session.execute(select(KnowledgeConcept))).scalars().all()
    }
    updated_concept_ids: list[UUID] = []

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
            await session.flush()

        updated_concept_ids.append(concept.id)
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

    active_normalized_terms = {normalized_term for normalized_term, candidate in candidates.items() if len(candidate.document_ids) >= 1}
    for normalized_term, concept in existing_concepts.items():
        if normalized_term not in active_normalized_terms and concept.status != ConceptStatus.ignored.value:
            concept.status = ConceptStatus.stale.value
            concept.refreshed_at = utcnow()

    await session.flush()
    return len(updated_concept_ids)


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

    concept.updated_at = utcnow()
    concept.refreshed_at = utcnow()
    await session.commit()
    return await get_glossary_concept_detail(session, concept.id)


async def create_or_regenerate_glossary_draft(
    session: AsyncSession,
    concept_id: UUID,
    payload: GlossaryDraftRequest,
) -> GlossaryConceptDetailResponse:
    concept = await _get_concept_or_raise(session, concept_id)
    if concept.generated_document_id is not None and not payload.regenerate:
        return await get_glossary_concept_detail(session, concept.id)
    from app.schemas.documents import IngestDocumentRequest
    from app.services.document_drafts import generate_definition_markdown_from_references
    from app.services.ingest import ingest_document

    support_hits = await get_concept_support_hits(session, concept.id, limit=8)
    if not support_hits:
        raise GlossaryError("No supporting evidence is available for this concept.")

    markdown, references = await generate_definition_markdown_from_references(
        topic=concept.display_term,
        domain=payload.domain,
        support_rows=support_hits,
        allow_fallback=True,
    )

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
    concept.updated_at = utcnow()
    concept.refreshed_at = utcnow()
    await session.commit()
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
