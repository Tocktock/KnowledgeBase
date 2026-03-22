from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db_session
from app.schemas.jobs import JobSummary
from app.services.jobs import get_job_summary, list_recent_jobs

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
async def list_jobs(session: AsyncSession = Depends(get_db_session)) -> list[JobSummary]:
    return await list_recent_jobs(session, limit=50)


@router.get("/{job_id}", response_model=JobSummary)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_db_session)) -> JobSummary:
    job = await get_job_summary(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
