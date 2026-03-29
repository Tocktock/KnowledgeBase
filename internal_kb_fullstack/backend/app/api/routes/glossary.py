from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user
from app.core.utils import utcnow
from app.db.engine import get_db_session
from app.db.models import GlossaryJob, GlossaryJobKind, GlossaryJobScope, JobStatus
from app.schemas.glossary import (
    GlossaryConceptDetailResponse,
    GlossaryConceptListResponse,
    GlossaryConceptUpdateRequest,
    GlossaryDraftRequest,
    GlossaryRefreshRequest,
    GlossaryValidationRunCreateRequest,
    GlossaryValidationRunListResponse,
    GlossaryValidationRunSummary,
)
from app.schemas.jobs import JobSummary
from app.services.auth import AuthenticatedUser
from app.services.glossary import (
    GlossaryError,
    GlossaryNotFoundError,
    create_glossary_validation_run,
    create_or_regenerate_glossary_draft,
    enqueue_glossary_refresh_job,
    get_glossary_validation_run,
    get_glossary_concept_by_slug,
    get_glossary_concept_detail,
    list_glossary_validation_runs,
    list_glossary_concepts,
    update_glossary_concept,
)
from app.services.document_drafts import DefinitionDraftConfigError, DefinitionDraftGenerationError

router = APIRouter(prefix="/v1/glossary", tags=["glossary"])


def _glossary_job_summary(job: GlossaryJob) -> JobSummary:
    title = "Glossary draft" if job.kind == GlossaryJobKind.draft.value else f"Glossary refresh ({job.scope})"
    return JobSummary.model_validate(job).model_copy(
        update={
            "kind": job.kind,
            "title": title,
        }
    )


def _require_workspace_glossary_manager(auth_user: AuthenticatedUser) -> None:
    if auth_user.current_workspace_id is None or not auth_user.can_manage_workspace_connectors:
        raise HTTPException(status_code=403, detail="Glossary validation runs require a workspace owner or admin.")


@router.post("/refresh", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def refresh_glossary_route(
    payload: GlossaryRefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JobSummary:
    _require_workspace_glossary_manager(auth_user)
    job = await enqueue_glossary_refresh_job(session, scope=payload.scope)
    await session.commit()
    await session.refresh(job)
    return _glossary_job_summary(job)


@router.post("/validation-runs", response_model=GlossaryValidationRunSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_glossary_validation_run_route(
    payload: GlossaryValidationRunCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> GlossaryValidationRunSummary:
    _require_workspace_glossary_manager(auth_user)
    try:
        return await create_glossary_validation_run(
            session,
            workspace_id=auth_user.current_workspace_id,
            requested_by_user_id=auth_user.user.id,
            payload=payload,
        )
    except GlossaryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/validation-runs", response_model=GlossaryValidationRunListResponse)
async def list_glossary_validation_runs_route(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> GlossaryValidationRunListResponse:
    _require_workspace_glossary_manager(auth_user)
    return await list_glossary_validation_runs(
        session,
        workspace_id=auth_user.current_workspace_id,
        limit=limit,
    )


@router.get("/validation-runs/{run_id}", response_model=GlossaryValidationRunSummary)
async def get_glossary_validation_run_route(
    run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> GlossaryValidationRunSummary:
    _require_workspace_glossary_manager(auth_user)
    try:
        return await get_glossary_validation_run(
            session,
            workspace_id=auth_user.current_workspace_id,
            run_id=run_id,
        )
    except GlossaryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=GlossaryConceptListResponse)
async def list_glossary_route(
    q: str | None = Query(default=None, alias="query"),
    status_filter: str | None = Query(default=None, alias="status"),
    concept_type: str | None = None,
    owner_team: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> GlossaryConceptListResponse:
    return await list_glossary_concepts(
        session,
        q=q,
        status_filter=status_filter,
        concept_type=concept_type,
        owner_team=owner_team,
        limit=limit,
        offset=offset,
    )


@router.get("/slug/{slug}", response_model=GlossaryConceptDetailResponse)
async def get_glossary_by_slug_route(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> GlossaryConceptDetailResponse:
    try:
        return await get_glossary_concept_by_slug(session, slug)
    except GlossaryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{concept_id}", response_model=GlossaryConceptDetailResponse)
async def get_glossary_concept_route(
    concept_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> GlossaryConceptDetailResponse:
    try:
        return await get_glossary_concept_detail(session, concept_id)
    except GlossaryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{concept_id}/draft", response_model=GlossaryConceptDetailResponse)
async def create_glossary_draft_route(
    concept_id: UUID,
    payload: GlossaryDraftRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> GlossaryConceptDetailResponse:
    _require_workspace_glossary_manager(auth_user)
    job = GlossaryJob(
        kind=GlossaryJobKind.draft.value,
        scope=GlossaryJobScope.incremental.value,
        status=JobStatus.processing.value,
        target_concept_id=concept_id,
        priority=60,
        attempt_count=1,
        payload={"domain": payload.domain, "regenerate": payload.regenerate},
        requested_at=utcnow(),
        started_at=utcnow(),
        last_heartbeat_at=utcnow(),
    )
    session.add(job)
    await session.flush()

    try:
        detail = await create_or_regenerate_glossary_draft(session, concept_id, payload)
    except GlossaryNotFoundError as exc:
        job.status = JobStatus.failed.value
        job.error_message = str(exc)
        job.finished_at = utcnow()
        await session.commit()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GlossaryError as exc:
        job.status = JobStatus.failed.value
        job.error_message = str(exc)
        job.finished_at = utcnow()
        await session.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DefinitionDraftConfigError as exc:
        job.status = JobStatus.failed.value
        job.error_message = str(exc)
        job.finished_at = utcnow()
        await session.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DefinitionDraftGenerationError as exc:
        job.status = JobStatus.failed.value
        job.error_message = str(exc)
        job.finished_at = utcnow()
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job.status = JobStatus.completed.value
    job.error_message = None
    job.finished_at = utcnow()
    job.last_heartbeat_at = utcnow()
    job.target_document_id = detail.concept.generated_document.id if detail.concept.generated_document is not None else None
    await session.commit()
    return detail


@router.patch("/{concept_id}", response_model=GlossaryConceptDetailResponse)
async def update_glossary_route(
    concept_id: UUID,
    payload: GlossaryConceptUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> GlossaryConceptDetailResponse:
    _require_workspace_glossary_manager(auth_user)
    try:
        return await update_glossary_concept(session, concept_id, payload)
    except GlossaryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GlossaryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
