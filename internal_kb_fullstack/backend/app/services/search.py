from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import vector_literal
from app.schemas.search import SearchHit, SearchRequest, SearchResponse
from app.services.embeddings import get_embedding_service


async def hybrid_search(session: AsyncSession, payload: SearchRequest) -> SearchResponse:
    settings = get_settings()
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.embed_one(payload.query)
    embedding_sql_literal = vector_literal(query_embedding)

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
              AND (:doc_type IS NULL OR d.doc_type = :doc_type)
              AND (:source_system IS NULL OR d.source_system = :source_system)
              AND (:owner_team IS NULL OR d.owner_team = :owner_team)
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
                row_number() OVER (ORDER BY embedding <=> CAST(:query_embedding AS vector({settings.embedding_dimensions}))) AS rank,
                1 - (embedding <=> CAST(:query_embedding AS vector({settings.embedding_dimensions}))) AS vector_score
            FROM current_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_embedding AS vector({settings.embedding_dimensions}))
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
            "query_embedding": embedding_sql_literal,
            "doc_type": payload.doc_type,
            "source_system": payload.source_system,
            "owner_team": payload.owner_team,
            "limit": payload.limit,
            "vector_candidates": settings.search_vector_candidates,
            "keyword_candidates": settings.search_keyword_candidates,
            "rrf_k": settings.search_rrf_k,
        },
    )

    hits = [SearchHit(**row) for row in result.mappings().all()]
    return SearchResponse(query=payload.query, hits=hits)
