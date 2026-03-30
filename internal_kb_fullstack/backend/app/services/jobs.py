from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import utcnow
from app.db.models import ConnectorResource, ConnectorSyncJob, Document, EmbeddingJob, GlossaryJob, JobStatus, KnowledgeConcept
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
    workspace_id: UUID | None,
    priority: int,
) -> EmbeddingJob | None:
    document, revision, _chunks = await get_document_detail(session, document_id, workspace_id=workspace_id)
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


def _connector_job_title(job: ConnectorSyncJob, resources_by_id: dict[UUID, ConnectorResource]) -> str:
    resource = resources_by_id.get(job.resource_id)
    if resource is not None:
        return f"리소스 동기화: {resource.name}"
    return "리소스 동기화"


async def list_recent_jobs(
    session: AsyncSession,
    *,
    workspace_id: UUID | None = None,
    limit: int = 50,
) -> list[JobSummary]:
    embedding_filters = []
    if workspace_id is not None:
        embedding_filters.append(Document.workspace_id == workspace_id)
    embedding_jobs = list(
        (
            await session.execute(
                select(EmbeddingJob)
                .join(Document, Document.id == EmbeddingJob.document_id)
                .where(*embedding_filters)
                .order_by(EmbeddingJob.requested_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    )
    glossary_filters = []
    if workspace_id is not None:
        glossary_filters.append(GlossaryJob.workspace_id == workspace_id)
    glossary_jobs = list(
        (
            await session.execute(
                select(GlossaryJob)
                .where(*glossary_filters)
                .order_by(GlossaryJob.requested_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    )
    connector_filters = []
    if workspace_id is not None:
        connector_filters.append(ConnectorConnection.workspace_id == workspace_id)
    connector_jobs = list(
        (
            await session.execute(
                select(ConnectorSyncJob)
                .join(ConnectorConnection, ConnectorConnection.id == ConnectorSyncJob.connection_id)
                .where(*connector_filters)
                .order_by(ConnectorSyncJob.requested_at.desc())
                .limit(limit)
            )
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
    resource_ids = {job.resource_id for job in connector_jobs}
    resources_by_id = {
        resource.id: resource
        for resource in (
            await session.execute(select(ConnectorResource).where(ConnectorResource.id.in_(resource_ids)))
        ).scalars().all()
    } if resource_ids else {}

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
                "title": _connector_job_title(job, resources_by_id),
                "resource_id": job.resource_id,
                "connection_id": job.connection_id,
            }
        )
        for job in connector_jobs
    ]
    return sorted(summaries, key=lambda item: item.requested_at, reverse=True)[:limit]


async def get_job_summary(
    session: AsyncSession,
    job_id: UUID,
    *,
    workspace_id: UUID | None = None,
) -> JobSummary | None:
    embedding_job = await session.get(EmbeddingJob, job_id)
    if embedding_job is not None:
        document = await session.get(Document, embedding_job.document_id)
        if workspace_id is not None and (document is None or document.workspace_id != workspace_id):
            return None
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
        if workspace_id is not None and glossary_job.workspace_id != workspace_id:
            return None
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

    resource = await session.get(ConnectorResource, connector_job.resource_id)
    if workspace_id is not None:
        connection = await session.get(ConnectorConnection, connector_job.connection_id)
        if connection is None or connection.workspace_id != workspace_id:
            return None
    return JobSummary.model_validate(connector_job).model_copy(
        update={
            "kind": connector_job.kind,
            "title": _connector_job_title(
                connector_job,
                {resource.id: resource} if resource is not None else {},
            ),
            "resource_id": connector_job.resource_id,
            "connection_id": connector_job.connection_id,
        }
    )
