from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Iterable

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from sqlalchemy import case, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.utils import normalize_whitespace, slugify
from app.db.models import Document, DocumentChunk
from app.schemas.documents import (
    DefinitionDraftReference,
    GenerateDefinitionDraftRequest,
    GenerateDefinitionDraftResponse,
)
from app.schemas.search import SearchHit, SearchRequest
from app.services.glossary import concept_search_key, get_concept_support_hits, resolve_concept
from app.services.search import hybrid_search
from app.services.trust import build_search_hit_trust

SECTION_TITLES = (
    "Definition",
    "How This Term Is Used Here",
    "Supporting Details",
    "Open Questions",
)
OPTIONAL_SECTION_TITLES = ("Observed Variants", "Notes")
CITATION_REQUIRED_SECTIONS = frozenset(SECTION_TITLES[:-1])
SECTION_HEADING_PATTERN = re.compile(r"^## (.+)$", flags=re.MULTILINE)
CITATION_PATTERN = re.compile(r"\[(\d+)\]")
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
HANGUL_PATTERN = re.compile(r"[가-힣]")


@dataclass(slots=True)
class ReferenceCandidate:
    reference: DefinitionDraftReference
    stage_rank: int
    score: float
    family_key: str
    order_index: int
    evidence_kind: str | None = None


class DefinitionDraftError(RuntimeError):
    pass


class DefinitionDraftConfigError(DefinitionDraftError):
    pass


class DefinitionDraftNotFoundError(DefinitionDraftError):
    pass


class DefinitionDraftGenerationError(DefinitionDraftError):
    pass


class DefinitionDraftValidationError(ValueError):
    pass


def build_definition_query(topic: str, domain: str | None = None) -> str:
    parts = [topic.strip()]
    if domain and domain.strip():
        parts.append(domain.strip())

    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for token in normalize_whitespace(part).split():
            normalized = token.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tokens.append(normalized)
    return " ".join(tokens)


def _trim_excerpt(text: str, *, limit: int = 420) -> str:
    normalized = normalize_whitespace(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _topic_particle_neun(topic: str) -> str:
    stripped = topic.strip()
    for char in reversed(stripped):
        if not HANGUL_PATTERN.match(char):
            continue
        code_point = ord(char) - 0xAC00
        jongseong = code_point % 28
        return "은" if jongseong else "는"
    return "는"


def _topic_particle_wa(topic: str) -> str:
    stripped = topic.strip()
    for char in reversed(stripped):
        if not HANGUL_PATTERN.match(char):
            continue
        code_point = ord(char) - 0xAC00
        jongseong = code_point % 28
        return "과" if jongseong else "와"
    return "와"


def _query_terms(topic: str, domain: str | None = None) -> list[str]:
    query = build_definition_query(topic, domain)
    return [term for term in _normalized_match_text(query).split() if term]


def _search_hit_match_text(hit: SearchHit) -> str:
    return " ".join(
        filter(
            None,
            [
                _normalized_match_text(hit.document_title),
                _normalized_match_text(hit.document_slug),
                _normalized_match_text(hit.section_title),
                " ".join(_normalized_match_text(item) for item in hit.heading_path),
                _normalized_match_text(hit.content_text),
            ],
        )
    )


def _query_match_score(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term in text)


def filter_relevant_search_hits(
    hits: Iterable[SearchHit],
    *,
    topic: str,
    domain: str | None = None,
) -> list[SearchHit]:
    terms = _query_terms(topic, domain)
    if not terms:
        return list(hits)

    relevant_hits: list[SearchHit] = []
    for hit in hits:
        if _query_match_score(_search_hit_match_text(hit), terms) >= 1:
            relevant_hits.append(hit)
    return relevant_hits


def select_reference_hits(hits: Iterable[SearchHit], *, limit: int) -> list[DefinitionDraftReference]:
    references: list[DefinitionDraftReference] = []
    seen: set[tuple[str, str | None, tuple[str, ...], str]] = set()
    staged_hits: list[tuple[SearchHit, tuple[str, str | None, tuple[str, ...], str]]] = []

    for hit in hits:
        excerpt = _trim_excerpt(hit.content_text)
        dedupe_key = (str(hit.document_id), hit.section_title, tuple(hit.heading_path), excerpt)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        staged_hits.append((hit, dedupe_key))

    seen_documents: set[str] = set()
    for hit, _dedupe_key in staged_hits:
        document_key = str(hit.document_id)
        if document_key in seen_documents:
            continue
        seen_documents.add(document_key)
        references.append(
            DefinitionDraftReference(
                index=len(references) + 1,
                document_id=hit.document_id,
                document_title=hit.document_title,
                document_slug=hit.document_slug,
                source_system=hit.source_system,
                source_url=hit.source_url,
                section_title=hit.section_title,
                heading_path=hit.heading_path,
                excerpt=_trim_excerpt(hit.content_text),
            )
        )
        if len(references) >= limit:
            return references

    for hit, _dedupe_key in staged_hits:
        if len(references) >= limit:
            break
        if any(reference.document_id == hit.document_id and reference.excerpt == _trim_excerpt(hit.content_text) for reference in references):
            continue
        references.append(
            DefinitionDraftReference(
                index=len(references) + 1,
                document_id=hit.document_id,
                document_title=hit.document_title,
                document_slug=hit.document_slug,
                source_system=hit.source_system,
                source_url=hit.source_url,
                section_title=hit.section_title,
                heading_path=hit.heading_path,
                excerpt=_trim_excerpt(hit.content_text),
            )
        )

    return references


def _reference_from_hit(hit: SearchHit) -> DefinitionDraftReference:
    return DefinitionDraftReference(
        index=0,
        document_id=hit.document_id,
        document_title=hit.document_title,
        document_slug=hit.document_slug,
        source_system=hit.source_system,
        source_url=hit.source_url,
        section_title=hit.section_title,
        heading_path=hit.heading_path,
        excerpt=_trim_excerpt(hit.content_text),
    )


def _family_key_for_reference(reference: DefinitionDraftReference) -> str:
    return concept_search_key(reference.document_title or reference.document_slug)


def _renumber_references(references: list[DefinitionDraftReference]) -> list[DefinitionDraftReference]:
    return [
        reference.model_copy(update={"index": index})
        for index, reference in enumerate(references, start=1)
    ]


def _reference_candidates_from_hits(
    hits: Iterable[SearchHit],
    *,
    stage_rank: int,
    score_fn: Callable[[SearchHit], float] | None = None,
) -> list[ReferenceCandidate]:
    candidates: list[ReferenceCandidate] = []
    seen: set[tuple[str, str, str | None]] = set()
    for order_index, hit in enumerate(hits):
        reference = _reference_from_hit(hit)
        dedupe_key = (
            str(reference.document_id),
            reference.excerpt,
            reference.section_title,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        score = float(score_fn(hit) if score_fn is not None else hit.hybrid_score)
        candidates.append(
            ReferenceCandidate(
                reference=reference,
                stage_rank=stage_rank,
                score=score,
                family_key=_family_key_for_reference(reference),
                order_index=order_index,
                evidence_kind=None,
            )
        )
    return candidates


def _reference_candidates_from_support_rows(rows: Iterable[dict[str, object]]) -> list[ReferenceCandidate]:
    candidates: list[ReferenceCandidate] = []
    seen: set[tuple[str, str, str | None]] = set()
    for order_index, row in enumerate(rows):
        excerpt = _trim_excerpt(str(row.get("content_text") or row.get("support_text") or ""))
        reference = DefinitionDraftReference(
            index=0,
            document_id=row["document_id"],
            document_title=str(row["document_title"]),
            document_slug=str(row["document_slug"]),
            source_system=str(row["source_system"]),
            source_url=row.get("source_url"),
            section_title=row.get("section_title"),
            heading_path=list(row.get("heading_path") or []),
            excerpt=excerpt,
        )
        dedupe_key = (
            str(reference.document_id),
            reference.excerpt,
            reference.section_title,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        evidence_kind = str(row.get("evidence_kind") or "semantic")
        stage_rank = 1 if evidence_kind in {"title", "alias"} else 2
        candidates.append(
            ReferenceCandidate(
                reference=reference,
                stage_rank=stage_rank,
                score=float(row.get("evidence_strength") or 0),
                family_key=str(row.get("support_group_key") or _family_key_for_reference(reference)),
                order_index=order_index,
                evidence_kind=evidence_kind,
            )
        )
    return candidates


def select_diverse_reference_candidates(
    candidates: Iterable[ReferenceCandidate],
    *,
    limit: int,
) -> list[DefinitionDraftReference]:
    staged = sorted(
        candidates,
        key=lambda candidate: (
            candidate.stage_rank,
            -candidate.score,
            candidate.order_index,
            candidate.reference.document_title,
        ),
    )
    selected: list[ReferenceCandidate] = []
    family_counts: dict[str, int] = {}
    document_counts: dict[str, int] = {}
    seen_blocks: set[tuple[str, str]] = set()

    def maybe_take(candidate: ReferenceCandidate, *, strict: bool) -> bool:
        document_key = str(candidate.reference.document_id)
        block_key = (document_key, candidate.reference.excerpt)
        if block_key in seen_blocks:
            return False
        if document_counts.get(document_key, 0) >= 2:
            return False
        family_key = candidate.family_key or document_key
        family_limit = 3 if candidate.stage_rank == 0 else 2
        if family_counts.get(family_key, 0) >= family_limit:
            return False
        if strict:
            if candidate.stage_rank != 0 and family_counts.get(family_key, 0) >= 1:
                return False
            if document_counts.get(document_key, 0) >= 1:
                return False
        selected.append(candidate)
        seen_blocks.add(block_key)
        family_counts[family_key] = family_counts.get(family_key, 0) + 1
        document_counts[document_key] = document_counts.get(document_key, 0) + 1
        return True

    for candidate in staged:
        if len(selected) >= limit:
            break
        maybe_take(candidate, strict=True)

    if len(selected) < limit:
        for candidate in staged:
            if len(selected) >= limit:
                break
            maybe_take(candidate, strict=False)

    return _renumber_references([candidate.reference for candidate in selected[:limit]])


async def fetch_exact_reference_hits(
    session: AsyncSession,
    payload: GenerateDefinitionDraftRequest,
    *,
    topic: str,
    limit: int,
) -> list[SearchHit]:
    normalized_topic = topic.strip()
    topic_slug = slugify(topic)
    if not normalized_topic:
        return []

    escaped_topic = re.escape(normalized_topic)
    escaped_topic_slug = re.escape(topic_slug)
    duplicate_title_pattern = rf"^{escaped_topic} \(\d+\)$"
    duplicate_slug_pattern = rf"^{escaped_topic_slug}(?:-\d+)?-[0-9a-f]{{10}}$"

    exact_match_rank = case(
        (Document.title == normalized_topic, 4),
        (Document.slug == topic_slug, 3),
        (Document.title.op("~")(duplicate_title_pattern), 2),
        (Document.slug.op("~")(duplicate_slug_pattern), 1),
        else_=0,
    )

    filters = [
        Document.status == "published",
        Document.current_revision_id == DocumentChunk.revision_id,
        exact_match_rank > 0,
    ]
    if payload.doc_type is not None:
        filters.append(Document.doc_type == payload.doc_type)
    if payload.source_system is not None:
        filters.append(Document.source_system == payload.source_system)
    if payload.owner_team is not None:
        filters.append(Document.owner_team == payload.owner_team)

    query = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id.label("document_id"),
            DocumentChunk.revision_id.label("revision_id"),
            Document.title.label("document_title"),
            Document.slug.label("document_slug"),
            Document.source_system.label("source_system"),
            Document.source_url.label("source_url"),
            Document.last_ingested_at.label("last_synced_at"),
            DocumentChunk.section_title.label("section_title"),
            DocumentChunk.heading_path.label("heading_path"),
            DocumentChunk.content_text.label("content_text"),
            exact_match_rank.label("hybrid_score"),
            literal(None).label("vector_score"),
            literal(None).label("keyword_score"),
            Document.meta.label("metadata"),
            literal(1).label("evidence_count"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(*filters)
        .order_by(
            exact_match_rank.desc(),
            case(
                (
                    or_(
                        DocumentChunk.section_title.ilike("%definition%"),
                        DocumentChunk.section_title.ilike("%개요%"),
                    ),
                    1,
                ),
                else_=0,
            ).desc(),
            DocumentChunk.chunk_index.asc(),
        )
        .limit(limit)
    )

    result = await session.execute(query)
    return [
        SearchHit(
            **row,
            trust=build_search_hit_trust(
                source_system=row["source_system"],
                source_url=row["source_url"],
                last_synced_at=row["last_synced_at"],
                evidence_count=row["evidence_count"],
                matched_concept=False,
            ),
        )
        for row in result.mappings().all()
    ]


async def gather_definition_reference_candidates(
    session: AsyncSession,
    payload: GenerateDefinitionDraftRequest,
    *,
    search_limit: int,
    reference_limit: int,
) -> tuple[object | None, list[ReferenceCandidate]]:
    query = build_definition_query(payload.topic, payload.domain)
    concept = await resolve_concept(session, payload.topic) if hasattr(session, "execute") else None

    search_response = await hybrid_search(
        session,
        SearchRequest(
            query=query,
            limit=search_limit,
            doc_type=payload.doc_type,
            source_system=payload.source_system,
            owner_team=payload.owner_team,
        ),
    )
    relevant_search_hits = filter_relevant_search_hits(
        search_response.hits,
        topic=payload.topic,
        domain=payload.domain,
    )
    exact_hits = await fetch_exact_reference_hits(
        session,
        payload,
        topic=payload.topic,
        limit=max(reference_limit * 3, 6),
    )

    support_rows: list[dict[str, object]] = []
    if concept is not None and hasattr(session, "execute"):
        support_rows = await get_concept_support_hits(
            session,
            concept.id,
            limit=max(reference_limit * 3, 8),
            owner_team=payload.owner_team,
            doc_type=payload.doc_type,
            source_system=payload.source_system,
        )

    candidates = [
        *_reference_candidates_from_hits(
            exact_hits,
            stage_rank=0,
            score_fn=lambda hit: float(hit.hybrid_score or 0),
        ),
        *_reference_candidates_from_support_rows(support_rows),
        *_reference_candidates_from_hits(
            relevant_search_hits,
            stage_rank=3,
            score_fn=lambda hit: float(hit.hybrid_score or 0),
        ),
    ]
    strong_family_count = len(
        {
            candidate.family_key
            for candidate in candidates
            if candidate.stage_rank <= 2 and candidate.family_key
        }
    )
    strong_document_count = len(
        {
            str(candidate.reference.document_id)
            for candidate in candidates
            if candidate.stage_rank <= 2
        }
    )
    if strong_family_count >= 2 or strong_document_count >= 3 or len(exact_hits) >= 2:
        candidates = [candidate for candidate in candidates if candidate.stage_rank <= 2]
    return concept, candidates


def _references_have_sufficient_grounding(
    references: list[DefinitionDraftReference],
    candidates_by_document: dict[str, ReferenceCandidate],
) -> bool:
    if not references:
        return False
    unique_documents = {str(reference.document_id) for reference in references}
    strong_documents = {
        str(reference.document_id)
        for reference in references
        if candidates_by_document[str(reference.document_id)].stage_rank <= 2
    }
    if strong_documents:
        return len(strong_documents) >= 2
    return len(unique_documents) >= 2


def _reference_location(reference: DefinitionDraftReference) -> str | None:
    parts = [part for part in [reference.section_title, *reference.heading_path] if part]
    if not parts:
        return None
    return " > ".join(parts)


def build_reference_section(references: list[DefinitionDraftReference]) -> str:
    lines = ["## References", ""]
    for reference in references:
        lines.append(f"{reference.index}. [{reference.document_title}](/docs/{reference.document_slug})")
        location = _reference_location(reference)
        if location:
            lines.append(f"   - Location: {location}")
        lines.append(f"   - Source system: {reference.source_system}")
        if reference.source_url:
            lines.append(f"   - Source: `{reference.source_url}`")
        lines.append(f"   - Excerpt: {reference.excerpt}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_fallback_body(
    *,
    topic: str,
    domain: str | None,
    references: list[DefinitionDraftReference],
) -> str:
    primary = references[0]
    secondary = references[1] if len(references) > 1 else primary
    topic_particle_wa = _topic_particle_wa(topic)
    supporting_lines = [
        f"- {reference.document_title}: {_trim_excerpt(reference.excerpt.replace(chr(10), ' / '))} [{reference.index}]"
        for reference in references[:3]
    ]
    family_count = len({_family_key_for_reference(reference) for reference in references})
    korean_first = HANGUL_PATTERN.search(topic or "") is not None or HANGUL_PATTERN.search(domain or "") is not None
    if korean_first:
        topic_particle = _topic_particle_neun(topic)
        body_lines = [
            "## Definition",
            f"{topic.strip()}{topic_particle} 현재 코퍼스의 근거 문서를 바탕으로 정리한 개념 초안입니다. [{primary.index}]",
            "",
            "## How This Term Is Used Here",
            f"현재 지식베이스에서는 {primary.document_title} 및 {secondary.document_title} 같은 문서에서 이 용어를 사용합니다. [{primary.index}][{secondary.index}]",
            "",
            "## Supporting Details",
            *supporting_lines,
        ]
    else:
        body_lines = [
            "## Definition",
            f"{topic.strip()} is a concept grounded in the current corpus and summarized from the referenced documents. [{primary.index}]",
            "",
            "## How This Term Is Used Here",
            f"In this knowledge base, the term appears in documents such as {primary.document_title} and {secondary.document_title}. [{primary.index}][{secondary.index}]",
            "",
            "## Supporting Details",
            *supporting_lines,
        ]
    if family_count > 1:
        if korean_first:
            body_lines.extend(
                [
                    "",
                    "## Observed Variants",
                    f"코퍼스에는 {topic.strip()}에 대한 여러 문서 계열 또는 관점이 함께 존재하므로, 편집 시 인용 출처 간 표현 차이를 조정해야 합니다. [{primary.index}]",
                ]
            )
        else:
            body_lines.extend(
                [
                    "",
                    "## Observed Variants",
                    f"The corpus contains multiple related document families or perspectives for {topic.strip()}, so editors should reconcile wording across the cited sources. [{primary.index}]",
                ]
            )
    body_lines.extend(
                [
                    "",
                    "## Open Questions",
                    (
                f"- {topic.strip()}{topic_particle_wa} 관련된 도메인별 예외 케이스 중 다음에 더 명확히 해야 할 항목은 무엇인가요?"
                if domain
                else f"- {topic.strip()}의 사용 범위와 경계를 더 명확히 해야 할 부분은 무엇인가요?"
            )
            if korean_first
            else (
                f"- Which domain-specific edge cases for {topic.strip()} should be clarified next?"
                if domain
                else f"- Which usage boundaries for {topic.strip()} should be clarified next?"
            ),
        ]
    )
    return "\n".join(body_lines).strip()


def _normalize_generated_body(markdown: str) -> str:
    body = normalize_whitespace(markdown)
    body = re.sub(r"^# .+\n+", "", body, count=1)
    body = re.split(r"\n## References\b", body, maxsplit=1)[0]
    body = _normalize_optional_section_titles(body)
    return body.strip()


def _normalize_optional_section_titles(body: str) -> str:
    matches = list(SECTION_HEADING_PATTERN.finditer(body))
    if len(matches) < 4:
        return body

    normalized_sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        normalized_sections.append((title, body[content_start:content_end].strip()))

    titles = [title for title, _content in normalized_sections]
    if titles[:3] != list(SECTION_TITLES[:3]) or SECTION_TITLES[-1] not in titles:
        return body

    open_questions_index = titles.index(SECTION_TITLES[-1])
    for index in range(3, open_questions_index):
        title, content = normalized_sections[index]
        if title not in OPTIONAL_SECTION_TITLES:
            normalized_sections[index] = ("Notes", content)

    return "\n\n".join(
        f"## {title}\n{content}".rstrip()
        for title, content in normalized_sections
    ).strip()


def build_reference_prompt(references: list[DefinitionDraftReference]) -> str:
    lines: list[str] = []
    for reference in references:
        lines.append(f"[{reference.index}] {reference.document_title}")
        lines.append(f"slug: {reference.document_slug}")
        lines.append(f"source_system: {reference.source_system}")
        if reference.source_url:
            lines.append(f"source_url: {reference.source_url}")
        location = _reference_location(reference)
        if location:
            lines.append(f"location: {location}")
        lines.append(f"excerpt: {reference.excerpt}")
        lines.append("")
    return "\n".join(lines).strip()


def _split_sections(body: str) -> list[tuple[str, str]]:
    body = _normalize_optional_section_titles(body)
    matches = list(SECTION_HEADING_PATTERN.finditer(body))
    if not matches:
        raise DefinitionDraftValidationError("Draft must contain the required sections.")

    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((title, body[content_start:content_end].strip()))

    titles = [title for title, _content in sections]
    if titles[:3] != list(SECTION_TITLES[:3]) or not titles or titles[-1] != SECTION_TITLES[-1]:
        expected = ", ".join([*SECTION_TITLES[:-1], f"[{' | '.join(OPTIONAL_SECTION_TITLES)}]", SECTION_TITLES[-1]])
        raise DefinitionDraftValidationError(f"Draft must contain sections in this order: {expected}.")
    middle_titles = titles[3:-1]
    if any(title not in OPTIONAL_SECTION_TITLES for title in middle_titles):
        allowed = ", ".join(OPTIONAL_SECTION_TITLES)
        raise DefinitionDraftValidationError(f"Only these optional sections are allowed before Open Questions: {allowed}.")
    return sections


def _iter_citable_blocks(content: str) -> list[str]:
    blocks: list[str] = []
    current_lines: list[str] = []
    current_kind: str | None = None

    def flush() -> None:
        nonlocal current_lines, current_kind
        if current_lines:
            blocks.append(" ".join(line.strip() for line in current_lines if line.strip()))
        current_lines = []
        current_kind = None

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            flush()
            continue

        is_list_item = LIST_ITEM_PATTERN.match(stripped) is not None
        if is_list_item:
            if current_kind == "list_item":
                flush()
            elif current_kind == "paragraph":
                flush()
            current_kind = "list_item"
            current_lines.append(stripped)
            continue

        if current_kind is None:
            current_kind = "paragraph"
        current_lines.append(stripped)

    flush()
    return [block for block in blocks if block]


def _citation_numbers(text: str) -> list[int]:
    return [int(match.group(1)) for match in CITATION_PATTERN.finditer(text)]


def _normalized_match_text(value: str | None) -> str:
    if not value:
        return ""
    return normalize_whitespace(value).replace("-", " ").replace("_", " ").lower()


def _split_raw_blocks(content: str) -> list[str]:
    blocks: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        if current_lines:
            blocks.append("\n".join(current_lines).strip())
        current_lines = []

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            flush()
            continue
        if LIST_ITEM_PATTERN.match(stripped):
            flush()
            blocks.append(stripped)
            continue
        current_lines.append(stripped)

    flush()
    return [block for block in blocks if block]


def _best_reference_index(block: str, references: list[DefinitionDraftReference]) -> int | None:
    block_terms = [term for term in _normalized_match_text(block).split() if term]
    if not block_terms:
        return None

    best_index: int | None = None
    best_score = 0
    for reference in references:
        reference_text = " ".join(
            filter(
                None,
                [
                    _normalized_match_text(reference.document_title),
                    _normalized_match_text(reference.section_title),
                    " ".join(_normalized_match_text(item) for item in reference.heading_path),
                    _normalized_match_text(reference.excerpt),
                ],
            )
        )
        score = sum(1 for term in block_terms if term in reference_text)
        if score > best_score:
            best_score = score
            best_index = reference.index
    return best_index if best_score > 0 else None


def repair_generated_body(body: str, references: list[DefinitionDraftReference]) -> str | None:
    sections = _split_sections(body)
    repaired_sections: list[tuple[str, str]] = []
    changed = False

    for title, content in sections:
        if title not in CITATION_REQUIRED_SECTIONS:
            repaired_sections.append((title, content))
            continue

        repaired_blocks: list[str] = []
        for block in _split_raw_blocks(content):
            if _citation_numbers(block):
                repaired_blocks.append(block)
                continue

            best_index = _best_reference_index(block, references)
            if best_index is None:
                return None
            repaired_blocks.append(f"{block} [{best_index}]")
            changed = True

        repaired_sections.append((title, "\n\n".join(repaired_blocks)))

    if not changed:
        return body

    return "\n\n".join(f"## {title}\n{content}".rstrip() for title, content in repaired_sections).strip()


def validate_generated_body(body: str, *, reference_count: int) -> None:
    sections = _split_sections(body)

    citations = _citation_numbers(body)
    if not citations:
        raise DefinitionDraftValidationError("Draft must contain at least one valid citation.")

    invalid_numbers = sorted({number for number in citations if number < 1 or number > reference_count})
    if invalid_numbers:
        joined = ", ".join(str(number) for number in invalid_numbers)
        raise DefinitionDraftValidationError(f"Draft cites references that do not exist: {joined}.")

    for title, content in sections:
        if title not in CITATION_REQUIRED_SECTIONS:
            continue
        for block in _iter_citable_blocks(content):
            if not _citation_numbers(block):
                raise DefinitionDraftValidationError(
                    f"Every paragraph or list item in '{title}' must include at least one citation."
                )


async def _generate_validated_body(
    *,
    generator: "DefinitionDraftGenerator",
    topic: str,
    domain: str | None,
    references: list[DefinitionDraftReference],
    initial_feedback: str | None = None,
) -> str:
    validation_feedback = initial_feedback
    body: str | None = None
    last_candidate_body: str | None = None

    for _attempt in range(2):
        candidate_body = await generator.generate_body(
            topic=topic,
            domain=domain,
            references=references,
            validation_feedback=validation_feedback,
        )
        last_candidate_body = candidate_body
        try:
            validate_generated_body(candidate_body, reference_count=len(references))
        except DefinitionDraftValidationError as exc:
            validation_feedback = str(exc)
            continue
        body = candidate_body
        break

    if body is not None:
        return body

    if last_candidate_body is not None:
        try:
            repaired_body = repair_generated_body(last_candidate_body, references)
        except DefinitionDraftValidationError as exc:
            raise DefinitionDraftGenerationError(str(exc)) from exc
        if repaired_body is not None:
            try:
                validate_generated_body(repaired_body, reference_count=len(references))
            except DefinitionDraftValidationError as exc:
                raise DefinitionDraftGenerationError(str(exc)) from exc
            return repaired_body

    raise DefinitionDraftGenerationError(validation_feedback or "The generated draft failed citation validation.")


async def _generate_quality_checked_body(
    *,
    generator: "DefinitionDraftGenerator",
    topic: str,
    domain: str | None,
    references: list[DefinitionDraftReference],
) -> str:
    body = await _generate_validated_body(
        generator=generator,
        topic=topic,
        domain=domain,
        references=references,
    )
    critique_fn = getattr(generator, "critique_body", None)
    if critique_fn is None:
        return body

    critique_feedback = await critique_fn(
        topic=topic,
        domain=domain,
        references=references,
        body=body,
    )
    if critique_feedback is None:
        return body

    revised_body = await _generate_validated_body(
        generator=generator,
        topic=topic,
        domain=domain,
        references=references,
        initial_feedback=f"Revise the draft to address this groundedness critique exactly:\n- {critique_feedback}",
    )
    second_critique = await critique_fn(
        topic=topic,
        domain=domain,
        references=references,
        body=revised_body,
    )
    if second_critique is not None:
        raise DefinitionDraftGenerationError(second_critique)
    return revised_body


class DefinitionDraftGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.generation_api_key or self.settings.embedding_api_key or None,
            base_url=self.settings.generation_base_url or self.settings.embedding_base_url or None,
            timeout=self.settings.generation_timeout_seconds,
        )

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def generate_body(
        self,
        *,
        topic: str,
        domain: str | None,
        references: list[DefinitionDraftReference],
        validation_feedback: str | None = None,
    ) -> str:
        if not self.settings.generation_model:
            raise DefinitionDraftConfigError(
                "GENERATION_MODEL is not configured. Set a chat-capable model before generating drafts."
            )

        retry_instruction = ""
        if validation_feedback:
            retry_instruction = (
                "\n\nThe previous draft failed validation. Fix these issues exactly and do not add any new unsupported "
                f"citations:\n- {validation_feedback}"
            )

        response = await self.client.chat.completions.create(
            model=self.settings.generation_model,
            temperature=self.settings.generation_temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write editable knowledge-base definition drafts grounded only in provided references. "
                        "Respond in markdown body only. Do not include a top-level title. Do not include a References "
                        "section. Use inline citations like [1] and only cite provided references. "
                        "Your body must contain exactly these sections in order: "
                        "## Definition, ## How This Term Is Used Here, ## Supporting Details, optional ## Observed Variants or ## Notes, and ## Open Questions. "
                        "Every paragraph or list item in the first three sections must include at least one valid citation. "
                        "If the references disagree or show meaningful variations, add ## Observed Variants or ## Notes before Open Questions."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic.strip()}\n"
                        f"Domain/context: {(domain or 'not specified').strip()}\n\n"
                        "Write a concise but useful draft with these sections:\n"
                        "## Definition\n"
                        "## How This Term Is Used Here\n"
                        "## Supporting Details\n"
                        "## Open Questions\n\n"
                        "Use the same primary language as the topic/context request, preserving domain terms as written. "
                        "Only use citations in the form [n], where n refers to the provided references."
                        f"{retry_instruction}\n\n"
                        f"References:\n{build_reference_prompt(references)}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise DefinitionDraftGenerationError("The model returned an empty draft.")

        body = _normalize_generated_body(content)
        if not body:
            raise DefinitionDraftGenerationError("The generated draft body was empty after normalization.")
        return body

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def critique_body(
        self,
        *,
        topic: str,
        domain: str | None,
        references: list[DefinitionDraftReference],
        body: str,
    ) -> str | None:
        if not self.settings.generation_model:
            raise DefinitionDraftConfigError(
                "GENERATION_MODEL is not configured. Set a chat-capable model before generating drafts."
            )

        response = await self.client.chat.completions.create(
            model=self.settings.generation_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict groundedness critic for a knowledge-base draft. "
                        "Evaluate whether the draft is fully supported by the provided references. "
                        "Check for unsupported generalizations, duplicate or repetitive claims, ambiguity that should be caveated, "
                        "and missing mention of meaningful variants in the references. "
                        "If the draft is acceptably grounded, respond with PASS only. "
                        "Otherwise respond with a concise bullet list of issues to fix."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic.strip()}\n"
                        f"Domain/context: {(domain or 'not specified').strip()}\n\n"
                        f"References:\n{build_reference_prompt(references)}\n\n"
                        f"Draft body:\n{body}"
                    ),
                },
            ],
        )
        content = normalize_whitespace(response.choices[0].message.content or "").strip()
        if not content or content.upper() == "PASS":
            return None
        return content


@lru_cache(maxsize=1)
def get_definition_draft_generator() -> DefinitionDraftGenerator:
    return DefinitionDraftGenerator()


async def generate_definition_markdown_from_references(
    *,
    topic: str,
    domain: str | None,
    references: list[DefinitionDraftReference] | None = None,
    support_rows: list[dict[str, object]] | None = None,
    allow_fallback: bool = False,
) -> tuple[str, list[DefinitionDraftReference]]:
    reference_list = list(references or [])
    if not reference_list and support_rows:
        reference_list = select_diverse_reference_candidates(
            _reference_candidates_from_support_rows(support_rows),
            limit=min(len(support_rows), 8),
        )
    if not reference_list:
        raise DefinitionDraftNotFoundError("No relevant references were found for this topic.")

    generator = get_definition_draft_generator()
    try:
        body = await _generate_quality_checked_body(
            generator=generator,
            topic=topic,
            domain=domain,
            references=reference_list,
        )
    except DefinitionDraftGenerationError:
        if not allow_fallback:
            raise
        body = build_fallback_body(
            topic=topic,
            domain=domain,
            references=reference_list,
        )
    lines = [f"# {topic.strip()}", ""]
    if domain and domain.strip():
        lines.extend([f"> Domain: {domain.strip()}", ""])
    lines.extend([body, "", build_reference_section(reference_list)])
    return "\n".join(lines).strip(), reference_list


async def generate_definition_draft(
    session: AsyncSession,
    payload: GenerateDefinitionDraftRequest,
) -> GenerateDefinitionDraftResponse:
    settings = get_settings()
    search_limit = payload.search_limit or settings.generation_search_limit
    reference_limit = payload.reference_limit or settings.generation_reference_limit
    query = build_definition_query(payload.topic, payload.domain)
    _concept, candidates = await gather_definition_reference_candidates(
        session,
        payload,
        search_limit=search_limit,
        reference_limit=reference_limit,
    )
    references = select_diverse_reference_candidates(candidates, limit=reference_limit)
    if not references:
        raise DefinitionDraftNotFoundError("No relevant references were found for this topic.")
    candidate_by_block = {
        (str(candidate.reference.document_id), candidate.reference.excerpt): candidate
        for candidate in candidates
    }
    strong_grounding = _references_have_sufficient_grounding(
        references,
        {
            str(reference.document_id): candidate_by_block[(str(reference.document_id), reference.excerpt)]
            for reference in references
        },
    )
    if not strong_grounding:
        raise DefinitionDraftNotFoundError("No relevant references were found for this topic.")

    markdown, references = await generate_definition_markdown_from_references(
        topic=payload.topic,
        domain=payload.domain,
        references=references,
        allow_fallback=strong_grounding,
    )

    return GenerateDefinitionDraftResponse(
        title=payload.topic.strip(),
        slug=slugify(payload.topic.strip()),
        query=query,
        markdown=markdown,
        references=references,
    )
