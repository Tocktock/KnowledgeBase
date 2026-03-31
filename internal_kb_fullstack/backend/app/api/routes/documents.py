from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user, get_optional_authenticated_user
from app.db.engine import get_db_session
from app.db.models import Document, DocumentRevision, EmbeddingJob
from app.schemas.documents import (
    ChunkSummary,
    DocumentContentResponse,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentRelationItem,
    DocumentRelationsResponse,
    DocumentSummary,
    DocumentViewResponse,
    GenerateDefinitionDraftRequest,
    GenerateDefinitionDraftResponse,
    HeadingSummary,
    IngestDocumentRequest,
    IngestDocumentResponse,
    RevisionSummary,
)
from app.schemas.jobs import JobSummary
from app.services.catalog import get_document_by_slug, get_document_detail, list_documents
from app.services.document_drafts import (
    DefinitionDraftConfigError,
    DefinitionDraftGenerationError,
    DefinitionDraftNotFoundError,
    generate_definition_draft,
)
from app.services.ingest import SlugConflictError, ingest_document
from app.services.jobs import request_document_reindex
from app.services.parser import DocumentParser
from app.services.source_urls import canonicalize_source_url
from app.services.auth import AuthenticatedUser
from app.services.trust import build_document_trust
from app.services.wiki_graph import extract_heading_items, extract_internal_slugs, get_document_relations
from app.services.workspace import resolve_read_workspace_id

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def _require_authoring_workspace(auth_user: AuthenticatedUser) -> UUID:
    if auth_user.current_workspace_id is None:
        raise HTTPException(status_code=403, detail="Document authoring requires an active workspace membership.")
    return auth_user.current_workspace_id


def _viewer_can_include_evidence_only(
    auth_user: AuthenticatedUser | None,
    *,
    workspace_id: UUID | None,
) -> bool:
    return bool(
        auth_user is not None
        and workspace_id is not None
        and auth_user.current_workspace_id == workspace_id
        and auth_user.can_manage_workspace_connectors
    )



def _document_summary(document: Document) -> DocumentSummary:
    canonical_source_url = canonicalize_source_url(
        source_system=document.source_system,
        source_url=document.source_url,
        source_external_id=document.source_external_id,
        slug=document.slug,
    )
    return DocumentSummary(
        id=document.id,
        source_system=document.source_system,
        source_external_id=document.source_external_id,
        source_url=canonical_source_url,
        slug=document.slug,
        title=document.title,
        language_code=document.language_code,
        doc_type=document.doc_type,
        status=document.status,
        visibility_scope=document.visibility_scope,
        owner_team=document.owner_team,
        metadata=document.meta,
        current_revision_id=document.current_revision_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        last_ingested_at=document.last_ingested_at,
        trust=build_document_trust(
            source_system=document.source_system,
            source_url=canonical_source_url,
            source_external_id=document.source_external_id,
            slug=document.slug,
            last_synced_at=document.last_ingested_at,
            doc_type=document.doc_type,
        ),
    )



def _revision_summary(revision: DocumentRevision) -> RevisionSummary:
    return RevisionSummary.model_validate(revision)



def _job_summary(job: EmbeddingJob | None) -> JobSummary | None:
    return JobSummary.model_validate(job) if job is not None else None



def _relation_item(row: dict) -> DocumentRelationItem:
    return DocumentRelationItem(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        excerpt=row.get("excerpt"),
        owner_team=row.get("owner_team"),
        doc_type=row["doc_type"],
        updated_at=row["updated_at"],
    )


def _slug_conflict_detail(document: Document) -> dict[str, object]:
    return {
        "code": "slug_conflict",
        "message": "A document with this slug already exists.",
        "document": {
            "id": str(document.id),
            "slug": document.slug,
            "title": document.title,
            "status": document.status,
            "owner_team": document.owner_team,
        },
    }


def _document_list_item(row: dict[str, object]) -> DocumentListItem:
    row_data = dict(row)
    canonical_source_url = canonicalize_source_url(
        source_system=str(row_data.get("source_system") or ""),
        source_url=row_data.get("source_url") if isinstance(row_data.get("source_url"), str) else None,
        source_external_id=row_data.get("source_external_id") if isinstance(row_data.get("source_external_id"), str) else None,
        slug=row_data.get("slug") if isinstance(row_data.get("slug"), str) else None,
    )
    row_data["source_url"] = canonical_source_url
    return DocumentListItem(
        **row_data,
        trust=build_document_trust(
            source_system=str(row_data.get("source_system") or ""),
            source_url=canonical_source_url,
            source_external_id=row_data.get("source_external_id") if isinstance(row_data.get("source_external_id"), str) else None,
            slug=row_data.get("slug") if isinstance(row_data.get("slug"), str) else None,
            last_synced_at=row_data.get("last_ingested_at"),  # type: ignore[arg-type]
            doc_type=row_data.get("doc_type") if isinstance(row_data.get("doc_type"), str) else None,
        ),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents_route(
    q: str | None = Query(default=None, alias="query"),
    owner_team: str | None = None,
    doc_type: list[str] | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> DocumentListResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    rows, total = await list_documents(
        session,
        workspace_id=workspace_id,
        q=q,
        owner_team=owner_team,
        doc_types=doc_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    items = [_document_list_item(row) for row in rows]
    return DocumentListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/ingest", response_model=IngestDocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document_route(
    payload: IngestDocumentRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> IngestDocumentResponse:
    workspace_id = _require_authoring_workspace(auth_user)
    try:
        result = await ingest_document(session, payload, workspace_id=workspace_id)
    except SlugConflictError as exc:
        raise HTTPException(status_code=409, detail=_slug_conflict_detail(exc.document)) from exc
    return IngestDocumentResponse(
        document=_document_summary(result.document),
        revision=_revision_summary(result.revision),
        job=_job_summary(result.job),
        unchanged=result.unchanged,
    )


@router.post("/upload", response_model=IngestDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_route(
    source_system: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    source_external_id: str | None = Form(default=None),
    source_revision_id: str | None = Form(default=None),
    source_url: str | None = Form(default=None),
    slug: str | None = Form(default=None),
    doc_type: str = Form(default="knowledge"),
    language_code: str = Form(default="ko"),
    owner_team: str | None = Form(default=None),
    status_value: str = Form(default="published", alias="status"),
    visibility_scope: str = Form(default="member_visible"),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> IngestDocumentResponse:
    workspace_id = _require_authoring_workspace(auth_user)
    parser = DocumentParser()
    content_type = parser.infer_content_type(file.filename or "uploaded.txt")
    content = (await file.read()).decode("utf-8", errors="ignore")
    payload = IngestDocumentRequest(
        source_system=source_system,
        source_external_id=source_external_id,
        source_revision_id=source_revision_id,
        source_url=source_url,
        slug=slug,
        title=title,
        content_type=content_type,
        content=content,
        doc_type=doc_type,
        language_code=language_code,
        owner_team=owner_team,
        status=status_value,  # type: ignore[arg-type]
        visibility_scope=visibility_scope,  # type: ignore[arg-type]
    )
    result = await ingest_document(session, payload, workspace_id=workspace_id)
    return IngestDocumentResponse(
        document=_document_summary(result.document),
        revision=_revision_summary(result.revision),
        job=_job_summary(result.job),
        unchanged=result.unchanged,
    )


@router.post("/generate-definition", response_model=GenerateDefinitionDraftResponse)
async def generate_definition_route(
    payload: GenerateDefinitionDraftRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> GenerateDefinitionDraftResponse:
    _require_authoring_workspace(auth_user)
    try:
        return await generate_definition_draft(session, payload)
    except DefinitionDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DefinitionDraftConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DefinitionDraftGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/slug/{slug}", response_model=DocumentViewResponse)
async def get_document_by_slug_route(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> DocumentViewResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    include_evidence_only = _viewer_can_include_evidence_only(auth_user, workspace_id=workspace_id)
    document, revision = await get_document_by_slug(
        session,
        slug=slug,
        workspace_id=workspace_id,
        include_evidence_only=include_evidence_only,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    _doc, _rev, chunks = await get_document_detail(
        session,
        document.id,
        workspace_id=workspace_id,
        include_evidence_only=include_evidence_only,
    )
    content_markdown = revision.content_markdown if revision is not None else None
    content_text = revision.content_text if revision is not None else None
    return DocumentViewResponse(
        document=_document_summary(document),
        revision=_revision_summary(revision) if revision is not None else None,
        content_markdown=content_markdown,
        content_text=content_text,
        headings=[HeadingSummary(**heading) for heading in extract_heading_items(content_markdown)],
        linked_slugs=extract_internal_slugs(content_markdown or ""),
        chunks=[ChunkSummary.model_validate(chunk) for chunk in chunks],
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_route(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> DocumentDetailResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    document, revision, chunks = await get_document_detail(
        session,
        document_id,
        workspace_id=workspace_id,
        include_evidence_only=_viewer_can_include_evidence_only(auth_user, workspace_id=workspace_id),
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        document=_document_summary(document),
        revision=_revision_summary(revision) if revision is not None else None,
        chunks=[ChunkSummary.model_validate(chunk) for chunk in chunks],
    )


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content_route(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> DocumentContentResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    document, revision, _chunks = await get_document_detail(
        session,
        document_id,
        workspace_id=workspace_id,
        include_evidence_only=_viewer_can_include_evidence_only(auth_user, workspace_id=workspace_id),
    )
    if document is None or revision is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentContentResponse(
        document_id=document.id,
        revision_id=revision.id,
        content_markdown=revision.content_markdown,
        content_text=revision.content_text,
    )


@router.get("/{document_id}/relations", response_model=DocumentRelationsResponse)
async def get_document_relations_route(
    document_id: UUID,
    limit: int = Query(default=8, ge=1, le=20),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> DocumentRelationsResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    relations = await get_document_relations(
        session,
        document_id=document_id,
        workspace_id=workspace_id,
        limit=limit,
        include_evidence_only=_viewer_can_include_evidence_only(auth_user, workspace_id=workspace_id),
    )
    return DocumentRelationsResponse(
        outgoing=[_relation_item(item) for item in relations["outgoing"]],
        backlinks=[_relation_item(item) for item in relations["backlinks"]],
        related=[_relation_item(item) for item in relations["related"]],
    )


@router.post("/{document_id}/reindex", response_model=JobSummary)
async def reindex_document_route(
    document_id: UUID,
    priority: int = 100,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JobSummary:
    workspace_id = _require_authoring_workspace(auth_user)
    job = await request_document_reindex(session, document_id=document_id, workspace_id=workspace_id, priority=priority)
    if job is None:
        raise HTTPException(status_code=404, detail="Document not found or has no current revision")
    return JobSummary.model_validate(job)
