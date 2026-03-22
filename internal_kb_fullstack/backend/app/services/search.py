from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import case, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import normalize_whitespace, vector_literal
from app.db.models import Document, DocumentChunk, KnowledgeConcept
from app.schemas.search import SearchExplainResponse, SearchHit, SearchRequest, SearchResponse
from app.services.embeddings import get_embedding_service
from app.services.glossary import concept_search_key, get_concept_support_hits, resolve_concept


@dataclass(slots=True)
class RankedHit:
    hit: SearchHit
    stage_rank: int
    sort_score: float
    family_key: str


def query_vector_sql(values: list[float], dimensions: int) -> str:
    return f"CAST('{vector_literal(values)}' AS vector({dimensions}))"


def current_chunk_filters_sql(payload: SearchRequest) -> tuple[str, dict[str, str]]:
    filters: list[str] = []
    params: dict[str, str] = {}

    if payload.doc_type is not None:
        filters.append("AND d.doc_type = :doc_type")
        params["doc_type"] = payload.doc_type

    if payload.source_system is not None:
        filters.append("AND d.source_system = :source_system")
        params["source_system"] = payload.source_system

    if payload.owner_team is not None:
        filters.append("AND d.owner_team = :owner_team")
        params["owner_team"] = payload.owner_team

    if not filters:
        return "", params

    return "\n              " + "\n              ".join(filters), params


def _normalized_match_text(value: str | None) -> str:
    if not value:
        return ""
    return normalize_whitespace(value).replace("-", " ").replace("_", " ").lower()


def _query_terms(query: str) -> list[str]:
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


def _is_lexically_relevant(hit: SearchHit, terms: list[str]) -> bool:
    if not terms:
        return True
    return _query_match_score(_search_hit_match_text(hit), terms) >= 1


def _family_key_for_hit(hit: SearchHit) -> str:
    return hit.support_group_key or concept_search_key(hit.document_title or hit.document_slug)


def _ranked_hit(hit: SearchHit, *, concept_document_ids: set[str]) -> RankedHit:
    family_key = _family_key_for_hit(hit) or str(hit.document_id)
    stage_rank = 3
    if hit.evidence_kind == "canonical":
        stage_rank = 0
    elif hit.matched_concept_id is not None and hit.evidence_kind in {"title", "alias"}:
        stage_rank = 1
    elif hit.matched_concept_id is not None or str(hit.document_id) in concept_document_ids:
        stage_rank = 2
    sort_score = float(hit.evidence_strength if hit.evidence_strength is not None else hit.hybrid_score)
    return RankedHit(hit=hit, stage_rank=stage_rank, sort_score=sort_score, family_key=family_key)


def _select_diverse_hits(hits: Iterable[SearchHit], *, limit: int, concept_document_ids: set[str]) -> list[SearchHit]:
    staged = sorted(
        (_ranked_hit(hit, concept_document_ids=concept_document_ids) for hit in hits),
        key=lambda ranked: (
            ranked.stage_rank,
            -ranked.sort_score,
            -float(ranked.hit.hybrid_score),
            ranked.hit.document_title,
            ranked.hit.content_text,
        ),
    )
    selected: list[RankedHit] = []
    family_counts: dict[str, int] = {}
    document_counts: dict[str, int] = {}
    seen_blocks: set[tuple[str, str]] = set()

    def maybe_take(ranked: RankedHit, *, strict: bool) -> None:
        if len(selected) >= limit:
            return
        document_key = str(ranked.hit.document_id)
        block_key = (document_key, normalize_whitespace(ranked.hit.content_text))
        if block_key in seen_blocks:
            return
        if document_counts.get(document_key, 0) >= 2:
            return
        if family_counts.get(ranked.family_key, 0) >= 2:
            return
        if strict:
            if family_counts.get(ranked.family_key, 0) >= 1:
                return
            if document_counts.get(document_key, 0) >= 1:
                return
        selected.append(ranked)
        seen_blocks.add(block_key)
        family_counts[ranked.family_key] = family_counts.get(ranked.family_key, 0) + 1
        document_counts[document_key] = document_counts.get(document_key, 0) + 1

    for ranked in staged:
        maybe_take(ranked, strict=True)
    for ranked in staged:
        maybe_take(ranked, strict=False)

    return [ranked.hit for ranked in selected[:limit]]


async def hybrid_search(session: AsyncSession, payload: SearchRequest) -> SearchResponse:
    settings = get_settings()
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.embed_one(payload.query)
    query_vector = query_vector_sql(query_embedding, settings.embedding_dimensions)
    current_chunk_filters, filter_params = current_chunk_filters_sql(payload)

    sql = text(
        f"""
        WITH current_chunks AS (
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.revision_id,
                d.title AS document_title,
                d.slug AS document_slug,
                d.source_system,
                d.source_url,
                d.metadata AS document_metadata,
                dc.section_title,
                dc.heading_path,
                dc.content_text,
                dc.search_vector,
                dc.embedding
            FROM document_chunks dc
            JOIN documents d
              ON d.id = dc.document_id
             AND d.current_revision_id = dc.revision_id
            WHERE d.status = 'published'
              {current_chunk_filters}
        ),
        vector_hits AS (
            SELECT
                chunk_id,
                document_id,
                revision_id,
                document_title,
                document_slug,
                source_system,
                source_url,
                document_metadata,
                section_title,
                heading_path,
                content_text,
                row_number() OVER (ORDER BY embedding <=> {query_vector}) AS rank,
                1 - (embedding <=> {query_vector}) AS vector_score
            FROM current_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> {query_vector}
            LIMIT :vector_candidates
        ),
        keyword_hits AS (
            SELECT
                chunk_id,
                document_id,
                revision_id,
                document_title,
                document_slug,
                source_system,
                source_url,
                document_metadata,
                section_title,
                heading_path,
                content_text,
                row_number() OVER (ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('simple', :query)) DESC) AS rank,
                ts_rank_cd(search_vector, websearch_to_tsquery('simple', :query)) AS keyword_score
            FROM current_chunks
            WHERE search_vector @@ websearch_to_tsquery('simple', :query)
            ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('simple', :query)) DESC
            LIMIT :keyword_candidates
        ),
        combined AS (
            SELECT
                chunk_id,
                document_id,
                revision_id,
                document_title,
                document_slug,
                source_system,
                source_url,
                document_metadata,
                section_title,
                heading_path,
                content_text,
                (1.0 / (:rrf_k + rank)) AS rrf_score,
                vector_score,
                NULL::double precision AS keyword_score
            FROM vector_hits
            UNION ALL
            SELECT
                chunk_id,
                document_id,
                revision_id,
                document_title,
                document_slug,
                source_system,
                source_url,
                document_metadata,
                section_title,
                heading_path,
                content_text,
                (1.0 / (:rrf_k + rank)) AS rrf_score,
                NULL::double precision AS vector_score,
                keyword_score
            FROM keyword_hits
        )
        SELECT
            chunk_id,
            document_id,
            revision_id,
            document_title,
            document_slug,
            source_system,
            source_url,
            section_title,
            heading_path,
            content_text,
            SUM(rrf_score) AS hybrid_score,
            MAX(vector_score) AS vector_score,
            MAX(keyword_score) AS keyword_score,
            'document' AS result_type,
            NULL::uuid AS matched_concept_id,
            NULL::text AS matched_concept_term,
            NULL::text AS evidence_kind,
            NULL::double precision AS evidence_strength,
            NULL::text AS support_group_key,
            document_metadata AS metadata
        FROM combined
        GROUP BY
            chunk_id,
            document_id,
            revision_id,
            document_title,
            document_slug,
            source_system,
            source_url,
            section_title,
            heading_path,
            content_text,
            document_metadata
        ORDER BY hybrid_score DESC
        LIMIT :limit
        """
    )

    result = await session.execute(
        sql,
        {
            "query": payload.query,
            "limit": payload.limit,
            "vector_candidates": settings.search_vector_candidates,
            "keyword_candidates": settings.search_keyword_candidates,
            "rrf_k": settings.search_rrf_k,
            **filter_params,
        },
    )

    hits = [SearchHit(**row) for row in result.mappings().all()]
    return SearchResponse(query=payload.query, hits=hits)


async def _fetch_canonical_glossary_hit(
    session: AsyncSession,
    *,
    concept: KnowledgeConcept,
) -> SearchHit | None:
    if concept.canonical_document_id is None:
        return None

    row = (
        await session.execute(
            select(
                DocumentChunk.id.label("chunk_id"),
                Document.id.label("document_id"),
                Document.current_revision_id.label("revision_id"),
                Document.title.label("document_title"),
                Document.slug.label("document_slug"),
                Document.source_system,
                Document.source_url,
                DocumentChunk.section_title,
                DocumentChunk.heading_path,
                DocumentChunk.content_text,
                literal(100.0).label("hybrid_score"),
                literal(None).label("vector_score"),
                literal(None).label("keyword_score"),
                literal("glossary").label("result_type"),
                literal(concept.id).label("matched_concept_id"),
                literal(concept.display_term).label("matched_concept_term"),
                literal("canonical").label("evidence_kind"),
                literal(float(concept.confidence_score) + 1.0).label("evidence_strength"),
                literal(concept_search_key(concept.display_term)).label("support_group_key"),
                Document.meta.label("metadata"),
            )
            .join(DocumentChunk, DocumentChunk.revision_id == Document.current_revision_id)
            .where(Document.id == concept.canonical_document_id)
            .order_by(
                case(
                    (
                        DocumentChunk.section_title.ilike("%definition%"),
                        2,
                    ),
                    (
                        DocumentChunk.section_title.ilike("%개요%"),
                        1,
                    ),
                    else_=0,
                ).desc(),
                DocumentChunk.chunk_index.asc(),
            )
            .limit(1)
        )
    ).mappings().first()
    if row is None:
        return None
    return SearchHit(**row)


def _support_row_to_hit(row: dict[str, object], *, concept: KnowledgeConcept) -> SearchHit:
    return SearchHit(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        revision_id=row["revision_id"],
        document_title=str(row["document_title"]),
        document_slug=str(row["document_slug"]),
        source_system=str(row["source_system"]),
        source_url=row.get("source_url"),
        section_title=row.get("section_title"),
        heading_path=list(row.get("heading_path") or []),
        content_text=str(row.get("content_text") or row.get("support_text") or ""),
        hybrid_score=float(row.get("evidence_strength") or 0) + 1.0,
        vector_score=None,
        keyword_score=None,
        result_type="glossary" if str(row.get("source_system")) == "glossary" else "document",
        matched_concept_id=concept.id,
        matched_concept_term=concept.display_term,
        evidence_kind=str(row.get("evidence_kind") or "semantic"),
        evidence_strength=float(row.get("evidence_strength") or 0),
        support_group_key=str(row.get("support_group_key") or concept_search_key(str(row["document_title"]))),
        metadata=dict(row.get("document_metadata") or {}),
    )


async def _assemble_concept_hits(
    session: AsyncSession,
    *,
    payload: SearchRequest,
    concept: KnowledgeConcept | None,
) -> tuple[list[SearchHit], str | None]:
    if concept is None:
        return [], None

    canonical_hit = await _fetch_canonical_glossary_hit(session, concept=concept)
    support_rows = await get_concept_support_hits(
        session,
        concept.id,
        limit=max(payload.limit * 4, 12),
        owner_team=payload.owner_team,
        doc_type=payload.doc_type,
        source_system=payload.source_system,
    )
    support_hits = [_support_row_to_hit(row, concept=concept) for row in support_rows]
    hits = ([canonical_hit] if canonical_hit is not None else []) + support_hits
    canonical_slug = canonical_hit.document_slug if canonical_hit is not None else None
    return hits, canonical_slug


async def search_documents(session: AsyncSession, payload: SearchRequest) -> SearchResponse:
    raw_response = await hybrid_search(session, payload)
    concept = await resolve_concept(session, payload.query)
    concept_hits, _canonical_slug = await _assemble_concept_hits(session, payload=payload, concept=concept)
    query_terms = _query_terms(payload.query)
    lexical_hits = [hit for hit in raw_response.hits if _is_lexically_relevant(hit, query_terms)]
    concept_document_ids = {str(hit.document_id) for hit in concept_hits}
    assembled_hits = _select_diverse_hits(
        [*concept_hits, *lexical_hits],
        limit=payload.limit,
        concept_document_ids=concept_document_ids,
    )
    weak_grounding = concept is not None and not any(
        hit.evidence_kind in {"canonical", "title", "alias", "heading"}
        for hit in assembled_hits
        if hit.matched_concept_id is not None
    )
    notes: list[str] = []
    if concept is not None and weak_grounding:
        notes.append("Resolved a concept candidate, but the available grounded evidence is weak.")
    if concept is None and not assembled_hits:
        notes.append("No grounded search hits passed lexical relevance filtering.")
    return SearchResponse(
        query=payload.query,
        resolved_concept_id=concept.id if concept is not None else None,
        resolved_concept_term=concept.display_term if concept is not None else None,
        weak_grounding=weak_grounding,
        notes=notes,
        hits=assembled_hits,
    )


async def explain_search(session: AsyncSession, payload: SearchRequest) -> SearchExplainResponse:
    raw_response = await hybrid_search(session, payload)
    concept = await resolve_concept(session, payload.query)
    concept_hits, canonical_slug = await _assemble_concept_hits(session, payload=payload, concept=concept)
    query_terms = _query_terms(payload.query)
    lexical_hits = [hit for hit in raw_response.hits if _is_lexically_relevant(hit, query_terms)]
    concept_document_ids = {str(hit.document_id) for hit in concept_hits}
    assembled_hits = _select_diverse_hits(
        [*concept_hits, *lexical_hits],
        limit=max(payload.limit, 12),
        concept_document_ids=concept_document_ids,
    )
    weak_grounding = concept is not None and not any(
        hit.evidence_kind in {"canonical", "title", "alias", "heading"}
        for hit in assembled_hits
        if hit.matched_concept_id is not None
    )
    notes: list[str] = []
    if concept is not None and weak_grounding:
        notes.append("The resolved concept does not yet have strong exact-title or canonical evidence under the active filters.")
    return SearchExplainResponse(
        query=payload.query,
        normalized_query=concept_search_key(payload.query),
        resolved_concept_id=concept.id if concept is not None else None,
        resolved_concept_term=concept.display_term if concept is not None else None,
        resolved_concept_status=concept.status if concept is not None else None,
        canonical_document_slug=canonical_slug,
        weak_grounding=weak_grounding,
        notes=notes,
        hits=assembled_hits,
    )
