from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    HeadingSummary,
    IngestDocumentRequest,
    IngestDocumentResponse,
    RevisionSummary,
)
from app.schemas.jobs import JobSummary
from app.services.catalog import get_document_by_slug, get_document_detail, list_documents
from app.services.ingest import ingest_document
from app.services.jobs import request_document_reindex
from app.services.parser import DocumentParser
from app.services.wiki_graph import extract_heading_items, extract_internal_slugs, get_document_relations

router = APIRouter(prefix="/v1/documents", tags=["documents"])



def _document_summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        source_system=document.source_system,
        source_external_id=document.source_external_id,
        source_url=document.source_url,
        slug=document.slug,
        title=document.title,
        language_code=document.language_code,
        doc_type=document.doc_type,
        status=document.status,
        owner_team=document.owner_team,
        metadata=document.meta,
        current_revision_id=document.current_revision_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        last_ingested_at=document.last_ingested_at,
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


@router.get("", response_model=DocumentListResponse)
async def list_documents_route(
    q: str | None = Query(default=None, alias="query"),
    owner_team: str | None = None,
    doc_type: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    rows, total = await list_documents(
        session,
        q=q,
        owner_team=owner_team,
        doc_type=doc_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    items = [DocumentListItem(**row) for row in rows]
    return DocumentListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/ingest", response_model=IngestDocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document_route(
    payload: IngestDocumentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> IngestDocumentResponse:
    result = await ingest_document(session, payload)
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
    session: AsyncSession = Depends(get_db_session),
) -> IngestDocumentResponse:
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
    )
    result = await ingest_document(session, payload)
    return IngestDocumentResponse(
        document=_document_summary(result.document),
        revision=_revision_summary(result.revision),
        job=_job_summary(result.job),
        unchanged=result.unchanged,
    )


@router.get("/slug/{slug}", response_model=DocumentViewResponse)
async def get_document_by_slug_route(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> DocumentViewResponse:
    document, revision = await get_document_by_slug(session, slug=slug)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    _doc, _rev, chunks = await get_document_detail(session, document.id)
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
) -> DocumentDetailResponse:
    document, revision, chunks = await get_document_detail(session, document_id)
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
) -> DocumentContentResponse:
    document, revision, _chunks = await get_document_detail(session, document_id)
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
) -> DocumentRelationsResponse:
    relations = await get_document_relations(session, document_id=document_id, limit=limit)
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
) -> JobSummary:
    job = await request_document_reindex(session, document_id=document_id, priority=priority)
    if job is None:
        raise HTTPException(status_code=404, detail="Document not found or has no current revision")
    return JobSummary.model_validate(job)
