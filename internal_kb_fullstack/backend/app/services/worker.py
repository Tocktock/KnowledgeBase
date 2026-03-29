from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.utils import utcnow
from app.db.models import ConnectorSyncJob, DocumentChunk, EmbeddingCache, EmbeddingJob, GlossaryJob, GlossaryJobKind, GlossaryValidationRun, JobStatus
from app.services.connectors import (
    acquire_next_connector_sync_job,
    enqueue_due_sync_jobs,
    mark_connector_job_failed,
    process_connector_sync_job,
)
from app.services.embeddings import get_embedding_service
from app.services.glossary import (
    create_or_regenerate_glossary_draft,
    execute_glossary_validation_run,
    refresh_glossary_concepts,
)


async def acquire_next_job(session: AsyncSession) -> EmbeddingJob | None:
    settings = get_settings()
    statement = text(
        """
        WITH candidate AS (
            SELECT id
            FROM embedding_jobs
            WHERE status IN ('queued', 'failed')
              AND attempt_count < :max_attempts
            ORDER BY priority ASC, requested_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE embedding_jobs j
        SET status = 'processing',
            started_at = now(),
            finished_at = NULL,
            last_heartbeat_at = now(),
            attempt_count = j.attempt_count + 1,
            error_message = NULL
        FROM candidate
        WHERE j.id = candidate.id
        RETURNING j.id
        """
    )
    result = await session.execute(statement, {"max_attempts": settings.worker_max_attempts})
    job_id = result.scalar_one_or_none()
    if job_id is None:
        return None
    return await session.get(EmbeddingJob, job_id)


async def acquire_next_glossary_job(session: AsyncSession) -> GlossaryJob | None:
    settings = get_settings()
    statement = text(
        """
        WITH candidate AS (
            SELECT id
            FROM glossary_jobs
            WHERE status IN ('queued', 'failed')
              AND attempt_count < :max_attempts
            ORDER BY priority ASC, requested_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE glossary_jobs j
        SET status = 'processing',
            started_at = now(),
            finished_at = NULL,
            last_heartbeat_at = now(),
            attempt_count = j.attempt_count + 1,
            error_message = NULL
        FROM candidate
        WHERE j.id = candidate.id
        RETURNING j.id
        """
    )
    result = await session.execute(statement, {"max_attempts": settings.worker_max_attempts})
    job_id = result.scalar_one_or_none()
    if job_id is None:
        return None
    return await session.get(GlossaryJob, job_id)


async def mark_job_failed(session: AsyncSession, job_id: UUID, message: str) -> None:
    await session.execute(
        text(
            """
            UPDATE embedding_jobs
            SET status = 'failed',
                error_message = :message,
                finished_at = now(),
                last_heartbeat_at = now()
            WHERE id = :job_id
            """
        ),
        {"job_id": job_id, "message": message[:4000]},
    )


async def mark_job_completed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE embedding_jobs
            SET status = 'completed',
                error_message = NULL,
                finished_at = now(),
                last_heartbeat_at = now()
            WHERE id = :job_id
            """
        ),
        {"job_id": job_id},
    )


async def heartbeat(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE embedding_jobs SET last_heartbeat_at = now() WHERE id = :job_id"),
        {"job_id": job_id},
    )


async def mark_glossary_job_failed(session: AsyncSession, job_id: UUID, message: str) -> None:
    job = await session.get(GlossaryJob, job_id)
    if job is not None and job.kind == GlossaryJobKind.validation_run.value:
        run_id = (job.payload or {}).get("run_id")
        if run_id:
            run = await session.get(GlossaryValidationRun, UUID(str(run_id)))
            if run is not None:
                run.status = JobStatus.failed.value
                run.error_message = message[:4000]
                run.finished_at = utcnow()
    await session.execute(
        text(
            """
            UPDATE glossary_jobs
            SET status = 'failed',
                error_message = :message,
                finished_at = now(),
                last_heartbeat_at = now()
            WHERE id = :job_id
            """
        ),
        {"job_id": job_id, "message": message[:4000]},
    )


async def mark_glossary_job_completed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE glossary_jobs
            SET status = 'completed',
                error_message = NULL,
                finished_at = now(),
                last_heartbeat_at = now()
            WHERE id = :job_id
            """
        ),
        {"job_id": job_id},
    )


async def heartbeat_glossary_job(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE glossary_jobs SET last_heartbeat_at = now() WHERE id = :job_id"),
        {"job_id": job_id},
    )


async def apply_cache_hits(session: AsyncSession, *, revision_id: UUID, model: str, dimensions: int) -> None:
    await session.execute(
        text(
            """
            UPDATE document_chunks dc
            SET embedding = ec.embedding,
                embedding_model = ec.embedding_model,
                embedding_dimensions = ec.embedding_dimensions,
                embedding_generated_at = now()
            FROM embedding_cache ec
            WHERE dc.revision_id = :revision_id
              AND dc.content_hash = ec.content_hash
              AND ec.embedding_model = :model
              AND ec.embedding_dimensions = :dimensions
              AND (
                    dc.embedding IS NULL
                 OR dc.embedding_model IS DISTINCT FROM ec.embedding_model
                 OR dc.embedding_dimensions IS DISTINCT FROM ec.embedding_dimensions
              )
            """
        ),
        {"revision_id": revision_id, "model": model, "dimensions": dimensions},
    )


async def get_missing_chunks(session: AsyncSession, *, revision_id: UUID, model: str, dimensions: int) -> list[DocumentChunk]:
    result = await session.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.revision_id == revision_id,
            (DocumentChunk.embedding.is_(None))
            | (DocumentChunk.embedding_model != model)
            | (DocumentChunk.embedding_dimensions != dimensions),
        )
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


async def persist_embeddings(
    session: AsyncSession,
    *,
    chunks: list[DocumentChunk],
    vectors: list[list[float]],
    model: str,
    dimensions: int,
) -> None:
    now = utcnow()

    cache_rows: list[dict[str, Any]] = []
    chunk_rows: list[dict[str, Any]] = []
    for chunk, embedding in zip(chunks, vectors, strict=True):
        cache_rows.append(
            {
                "content_hash": chunk.content_hash,
                "embedding_model": model,
                "embedding_dimensions": dimensions,
                "token_count": chunk.content_tokens,
                "embedding": embedding,
                "created_at": now,
            }
        )
        chunk_rows.append(
            {
                "chunk_id": chunk.id,
                "embedding": embedding,
                "embedding_model": model,
                "embedding_dimensions": dimensions,
                "generated_at": now,
            }
        )

    if cache_rows:
        stmt = pg_insert(EmbeddingCache).values(cache_rows).on_conflict_do_nothing(
            constraint="uq_embedding_cache_lookup"
        )
        await session.execute(stmt)

    if chunk_rows:
        await session.execute(
            text(
                """
                UPDATE document_chunks
                SET embedding = :embedding,
                    embedding_model = :embedding_model,
                    embedding_dimensions = :embedding_dimensions,
                    embedding_generated_at = :generated_at
                WHERE id = :chunk_id
                """
            ),
            chunk_rows,
        )


async def process_job(session_factory: async_sessionmaker[AsyncSession], job_id: UUID) -> None:
    embedding_service = get_embedding_service()

    async with session_factory() as session:
        job = await session.get(EmbeddingJob, job_id)
        if job is None:
            return
        await apply_cache_hits(
            session,
            revision_id=job.revision_id,
            model=job.embedding_model,
            dimensions=job.embedding_dimensions,
        )
        await heartbeat(session, job.id)
        await session.commit()

    async with session_factory() as session:
        job = await session.get(EmbeddingJob, job_id)
        if job is None:
            return

        missing_chunks = await get_missing_chunks(
            session,
            revision_id=job.revision_id,
            model=job.embedding_model,
            dimensions=job.embedding_dimensions,
        )
        if not missing_chunks:
            await mark_job_completed(session, job.id)
            await session.commit()
            return

        vectors = await embedding_service.embed_many([chunk.content_text for chunk in missing_chunks])
        await persist_embeddings(
            session,
            chunks=missing_chunks,
            vectors=vectors,
            model=job.embedding_model,
            dimensions=job.embedding_dimensions,
        )
        await mark_job_completed(session, job.id)
        await session.commit()


async def process_glossary_job(session_factory: async_sessionmaker[AsyncSession], job_id: UUID) -> None:
    async with session_factory() as session:
        job = await session.get(GlossaryJob, job_id)
        if job is None:
            return

        await heartbeat_glossary_job(session, job.id)
        if job.kind == GlossaryJobKind.refresh.value:
            updated_count = await refresh_glossary_concepts(
                session,
                scope=job.scope,
                target_document_id=job.target_document_id,
            )
            job.payload = {**(job.payload or {}), "updated_concepts": updated_count}
            await mark_glossary_job_completed(session, job.id)
            await session.commit()
            return

        if job.kind == GlossaryJobKind.draft.value:
            if job.target_concept_id is None:
                raise RuntimeError("Glossary draft job is missing target_concept_id.")
            detail = await create_or_regenerate_glossary_draft(
                session,
                job.target_concept_id,
                payload=dict_to_glossary_draft_payload(job.payload),
            )
            job.target_document_id = detail.concept.generated_document.id if detail.concept.generated_document is not None else None
            await mark_glossary_job_completed(session, job.id)
            await session.commit()
            return

        if job.kind == GlossaryJobKind.validation_run.value:
            run_id = (job.payload or {}).get("run_id")
            if not run_id:
                raise RuntimeError("Glossary validation job is missing run_id.")
            run = await execute_glossary_validation_run(session, UUID(str(run_id)))
            job.payload = {
                **(job.payload or {}),
                "run_id": str(run.id),
                "validation_summary": run.validation_summary,
            }
            await mark_glossary_job_completed(session, job.id)
            await session.commit()
            return

        raise RuntimeError(f"Unsupported glossary job kind: {job.kind}")


def dict_to_glossary_draft_payload(payload: dict[str, Any] | None):
    from app.schemas.glossary import GlossaryDraftRequest

    payload = payload or {}
    return GlossaryDraftRequest(
        domain=payload.get("domain"),
        regenerate=bool(payload.get("regenerate", True)),
    )


async def run_worker_loop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    settings = get_settings()
    configure_logging()

    while True:
        async with session_factory() as session:
            await enqueue_due_sync_jobs(session)
            connector_job: ConnectorSyncJob | None = await acquire_next_connector_sync_job(session)
            await session.commit()

        if connector_job is not None:
            try:
                await process_connector_sync_job(session_factory, connector_job.id)
            except Exception as exc:  # noqa: BLE001
                async with session_factory() as session:
                    await mark_connector_job_failed(session, connector_job.id, str(exc))
                    await session.commit()
                await asyncio.sleep(settings.worker_poll_seconds)
            continue

        async with session_factory() as session:
            job = await acquire_next_job(session)
            await session.commit()

        if job is None:
            async with session_factory() as session:
                glossary_job = await acquire_next_glossary_job(session)
                await session.commit()
            if glossary_job is None:
                await asyncio.sleep(settings.worker_idle_sleep_seconds)
                continue
            try:
                await process_glossary_job(session_factory, glossary_job.id)
            except Exception as exc:  # noqa: BLE001
                async with session_factory() as session:
                    await mark_glossary_job_failed(session, glossary_job.id, str(exc))
                    await session.commit()
                await asyncio.sleep(settings.worker_poll_seconds)
            continue

        try:
            await process_job(session_factory, job.id)
        except Exception as exc:  # noqa: BLE001
            async with session_factory() as session:
                await mark_job_failed(session, job.id, str(exc))
                await session.commit()
            await asyncio.sleep(settings.worker_poll_seconds)
