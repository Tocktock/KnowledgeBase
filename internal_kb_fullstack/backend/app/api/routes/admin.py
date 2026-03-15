from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db_session
from app.db.models import EmbeddingJob
from app.schemas.jobs import JobSummary

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
async def list_jobs(session: AsyncSession = Depends(get_db_session)) -> list[JobSummary]:
    result = await session.execute(select(EmbeddingJob).order_by(EmbeddingJob.requested_at.desc()).limit(50))
    return [JobSummary.model_validate(job) for job in result.scalars().all()]


@router.get("/{job_id}", response_model=JobSummary)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_db_session)) -> JobSummary:
    job = await session.get(EmbeddingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobSummary.model_validate(job)
