from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import utcnow
from app.db.models import EmbeddingJob, JobStatus
from app.services.catalog import get_document_detail


async def create_embedding_job(
    session: AsyncSession,
    *,
    document_id: UUID,
    revision_id: UUID,
    priority: int,
) -> EmbeddingJob:
    settings = get_settings()
    stmt = (
        pg_insert(EmbeddingJob)
        .values(
            document_id=document_id,
            revision_id=revision_id,
            status=JobStatus.queued.value,
            embedding_model=settings.embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
            priority=priority,
            attempt_count=0,
            error_message=None,
            requested_at=utcnow(),
            started_at=None,
            last_heartbeat_at=None,
            finished_at=None,
        )
        .on_conflict_do_update(
            constraint="uq_embedding_job_revision_model",
            set_={
                "status": JobStatus.queued.value,
                "batch_size": settings.embedding_batch_size,
                "priority": priority,
                "attempt_count": 0,
                "error_message": None,
                "requested_at": utcnow(),
                "started_at": None,
                "last_heartbeat_at": None,
                "finished_at": None,
            },
        )
        .returning(EmbeddingJob.id)
    )
    job_id = (await session.execute(stmt)).scalar_one()
    job = await session.get(EmbeddingJob, job_id)
    assert job is not None
    return job


async def request_document_reindex(
    session: AsyncSession,
    *,
    document_id: UUID,
    priority: int,
) -> EmbeddingJob | None:
    document, revision, _chunks = await get_document_detail(session, document_id)
    if document is None or revision is None:
        return None

    job = await create_embedding_job(
        session,
        document_id=document.id,
        revision_id=revision.id,
        priority=priority,
    )
    await session.commit()
    await session.refresh(job)
    return job
