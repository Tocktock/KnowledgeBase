from __future__ import annotations

import asyncio

from sqlalchemy import or_, select, text

from app.core.config import get_settings
from app.db.engine import get_session_factory
from app.db.models import DocumentChunk
from app.services.embeddings import get_embedding_service
from app.services.worker import persist_embeddings

SEGMENT_SIZE = 1024


async def count_progress() -> tuple[int, int]:
    settings = get_settings()
    async with get_session_factory()() as session:
        result = await session.execute(
            text(
                """
                SELECT
                  count(*) FILTER (
                    WHERE embedding IS NOT NULL
                      AND embedding_model = :model
                      AND embedding_dimensions = :dimensions
                  ) AS embedded,
                  count(*) AS total
                FROM document_chunks
                """
            ),
            {"model": settings.embedding_model, "dimensions": settings.embedding_dimensions},
        )
        row = result.mappings().one()
        return int(row["embedded"]), int(row["total"])


async def finalize_jobs() -> None:
    settings = get_settings()
    async with get_session_factory()() as session:
        await session.execute(
            text(
                """
                UPDATE embedding_jobs j
                SET status = 'completed',
                    error_message = NULL,
                    finished_at = now(),
                    last_heartbeat_at = now()
                WHERE status IN ('queued', 'failed', 'processing')
                  AND j.embedding_model = :model
                  AND j.embedding_dimensions = :dimensions
                  AND NOT EXISTS (
                    SELECT 1
                    FROM document_chunks dc
                    WHERE dc.revision_id = j.revision_id
                      AND (
                        dc.embedding IS NULL
                        OR dc.embedding_model IS DISTINCT FROM :model
                        OR dc.embedding_dimensions IS DISTINCT FROM :dimensions
                      )
                  )
                """
            ),
            {"model": settings.embedding_model, "dimensions": settings.embedding_dimensions},
        )
        await session.commit()


async def persist_segment(chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
    settings = get_settings()
    async with get_session_factory()() as session:
        await persist_embeddings(
            session,
            chunks=chunks,
            vectors=vectors,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
        await session.commit()
    await finalize_jobs()


async def process_segment(segment_index: int) -> bool:
    settings = get_settings()
    embedding_service = get_embedding_service()

    async with get_session_factory()() as session:
        async with session.begin():
            result = await session.execute(
                select(DocumentChunk)
                .where(
                    or_(
                        DocumentChunk.embedding.is_(None),
                        DocumentChunk.embedding_model != settings.embedding_model,
                        DocumentChunk.embedding_dimensions != settings.embedding_dimensions,
                    )
                )
                .order_by(DocumentChunk.revision_id.asc(), DocumentChunk.chunk_index.asc())
                .with_for_update(skip_locked=True)
                .limit(SEGMENT_SIZE)
            )
            chunks = list(result.scalars().all())
            if not chunks:
                return False

            vectors = await embedding_service.embed_many([chunk.content_text for chunk in chunks])
            await persist_embeddings(
                session,
                chunks=chunks,
                vectors=vectors,
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
            )

    await finalize_jobs()
    embedded_now, total = await count_progress()
    print(
        {
            "event": "segment",
            "segment": segment_index,
            "segment_chunks": len(chunks),
            "embedded_now": embedded_now,
            "remaining": total - embedded_now,
        },
        flush=True,
    )
    return True


async def main() -> None:
    embedded_before, total = await count_progress()
    print(
        {
            "event": "start",
            "embedded_before": embedded_before,
            "total_chunks": total,
            "segment_size": SEGMENT_SIZE,
        },
        flush=True,
    )

    segment_index = 0
    while True:
        segment_index += 1
        processed = await process_segment(segment_index)
        if not processed:
            break

    await finalize_jobs()
    embedded_after, total = await count_progress()
    print({"event": "done", "embedded_after": embedded_after, "total_chunks": total}, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
