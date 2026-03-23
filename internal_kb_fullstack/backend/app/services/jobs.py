from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import utcnow
from app.db.models import ConnectorSyncJob, ConnectorSyncTarget, Document, EmbeddingJob, GlossaryJob, JobStatus, KnowledgeConcept
from app.schemas.jobs import JobSummary
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


def _embedding_job_title(job: EmbeddingJob, documents_by_id: dict[UUID, Document]) -> str:
    document = documents_by_id.get(job.document_id)
    return f"Embedding reindex: {document.title}" if document is not None else "Embedding reindex"


def _glossary_job_title(job: GlossaryJob, concepts_by_id: dict[UUID, KnowledgeConcept]) -> str:
    if job.kind == "refresh":
        return f"Glossary refresh ({job.scope})"
    if job.target_concept_id is not None:
        concept = concepts_by_id.get(job.target_concept_id)
        if concept is not None:
            return f"Glossary draft: {concept.display_term}"
    return "Glossary draft"


def _connector_job_title(job: ConnectorSyncJob, targets_by_id: dict[UUID, ConnectorSyncTarget]) -> str:
    target = targets_by_id.get(job.target_id)
    if target is not None:
        return f"Drive 동기화: {target.name}"
    return "Drive 동기화"


async def list_recent_jobs(session: AsyncSession, *, limit: int = 50) -> list[JobSummary]:
    embedding_jobs = list(
        (
            await session.execute(select(EmbeddingJob).order_by(EmbeddingJob.requested_at.desc()).limit(limit))
        ).scalars().all()
    )
    glossary_jobs = list(
        (
            await session.execute(select(GlossaryJob).order_by(GlossaryJob.requested_at.desc()).limit(limit))
        ).scalars().all()
    )
    connector_jobs = list(
        (
            await session.execute(select(ConnectorSyncJob).order_by(ConnectorSyncJob.requested_at.desc()).limit(limit))
        ).scalars().all()
    )
    document_ids = {job.document_id for job in embedding_jobs}
    documents_by_id = {
        document.id: document
        for document in (
            await session.execute(select(Document).where(Document.id.in_(document_ids)))
        ).scalars().all()
    } if document_ids else {}
    concept_ids = {job.target_concept_id for job in glossary_jobs if job.target_concept_id is not None}
    concepts_by_id = {
        concept.id: concept
        for concept in (
            await session.execute(select(KnowledgeConcept).where(KnowledgeConcept.id.in_(concept_ids)))
        ).scalars().all()
    } if concept_ids else {}
    target_ids = {job.target_id for job in connector_jobs}
    targets_by_id = {
        target.id: target
        for target in (
            await session.execute(select(ConnectorSyncTarget).where(ConnectorSyncTarget.id.in_(target_ids)))
        ).scalars().all()
    } if target_ids else {}

    summaries = [
        JobSummary.model_validate(job).model_copy(
            update={
                "kind": "embedding",
                "title": _embedding_job_title(job, documents_by_id),
                "target_document_id": job.document_id,
            }
        )
        for job in embedding_jobs
    ] + [
        JobSummary.model_validate(job).model_copy(
            update={
                "kind": job.kind,
                "title": _glossary_job_title(job, concepts_by_id),
            }
        )
        for job in glossary_jobs
    ] + [
        JobSummary.model_validate(job).model_copy(
            update={
                "kind": job.kind,
                "title": _connector_job_title(job, targets_by_id),
                "target_id": job.target_id,
                "connection_id": job.connection_id,
            }
        )
        for job in connector_jobs
    ]
    return sorted(summaries, key=lambda item: item.requested_at, reverse=True)[:limit]


async def get_job_summary(session: AsyncSession, job_id: UUID) -> JobSummary | None:
    embedding_job = await session.get(EmbeddingJob, job_id)
    if embedding_job is not None:
        document = await session.get(Document, embedding_job.document_id)
        return JobSummary.model_validate(embedding_job).model_copy(
            update={
                "kind": "embedding",
                "title": _embedding_job_title(
                    embedding_job,
                    {document.id: document} if document is not None else {},
                ),
                "target_document_id": embedding_job.document_id,
            }
        )

    glossary_job = await session.get(GlossaryJob, job_id)
    if glossary_job is not None:
        concept = await session.get(KnowledgeConcept, glossary_job.target_concept_id) if glossary_job.target_concept_id is not None else None
        return JobSummary.model_validate(glossary_job).model_copy(
            update={
                "kind": glossary_job.kind,
                "title": _glossary_job_title(
                    glossary_job,
                    {concept.id: concept} if concept is not None else {},
                ),
            }
        )

    connector_job = await session.get(ConnectorSyncJob, job_id)
    if connector_job is None:
        return None

    target = await session.get(ConnectorSyncTarget, connector_job.target_id)
    return JobSummary.model_validate(connector_job).model_copy(
        update={
            "kind": connector_job.kind,
            "title": _connector_job_title(
                connector_job,
                {target.id: target} if target is not None else {},
            ),
            "target_id": connector_job.target_id,
            "connection_id": connector_job.connection_id,
        }
    )
