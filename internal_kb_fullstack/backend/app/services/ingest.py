from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import normalize_whitespace, sha256_text, slugify, utcnow
from app.db.models import Document, DocumentChunk, DocumentRevision, EmbeddingJob
from app.schemas.documents import IngestDocumentRequest
from app.services.chunking import TokenAwareChunker
from app.services.jobs import create_embedding_job
from app.services.parser import DocumentParser, ParsedContent
from app.services.wiki_graph import sync_document_links


@dataclass(slots=True)
class IngestResult:
    document: Document
    revision: DocumentRevision
    job: EmbeddingJob | None
    unchanged: bool


@dataclass(slots=True)
class DocumentMatch:
    document: Document | None
    matched_by: Literal["none", "source_external_id", "slug"]


class SlugConflictError(RuntimeError):
    def __init__(self, document: Document) -> None:
        super().__init__("A document with this slug already exists.")
        self.document = document


async def _get_document_by_slug(
    session: AsyncSession,
    slug: str,
    *,
    workspace_id: UUID | None = None,
    exclude_id: UUID | None = None,
) -> Document | None:
    query = select(Document).where(Document.slug == slug)
    if workspace_id is not None:
        query = query.where(Document.workspace_id == workspace_id)
    if exclude_id is not None:
        query = query.where(Document.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def _find_document(
    session: AsyncSession,
    payload: IngestDocumentRequest,
    resolved_slug: str,
    *,
    workspace_id: UUID | None = None,
) -> DocumentMatch:
    if payload.source_external_id:
        filters = [
            Document.source_system == payload.source_system,
            Document.source_external_id == payload.source_external_id,
        ]
        if workspace_id is not None:
            filters.append(Document.workspace_id == workspace_id)
        result = await session.execute(select(Document).where(*filters))
        document = result.scalar_one_or_none()
        if document is not None:
            return DocumentMatch(document=document, matched_by="source_external_id")

    document = await _get_document_by_slug(session, resolved_slug, workspace_id=workspace_id)
    if document is not None:
        return DocumentMatch(document=document, matched_by="slug")
    return DocumentMatch(document=None, matched_by="none")


async def _next_revision_number(session: AsyncSession, document_id: UUID) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(DocumentRevision.revision_number), 0)).where(DocumentRevision.document_id == document_id)
    )
    return int(result.scalar_one()) + 1


async def _upsert_document(
    session: AsyncSession,
    *,
    payload: IngestDocumentRequest,
    resolved_slug: str,
    workspace_id: UUID,
) -> Document:
    match = await _find_document(session, payload, resolved_slug, workspace_id=workspace_id)
    document = match.document

    if document is None:
        document = Document(
            workspace_id=workspace_id,
            source_system=payload.source_system,
            source_external_id=payload.source_external_id,
            source_url=payload.source_url,
            slug=resolved_slug,
            title=payload.title,
            language_code=payload.language_code,
            doc_type=payload.doc_type,
            status=payload.status,
            visibility_scope=payload.visibility_scope,
            owner_team=payload.owner_team,
            meta=payload.metadata,
            current_revision_id=None,
            last_ingested_at=utcnow(),
        )
        session.add(document)
        await session.flush()
        return document

    if match.matched_by == "slug" and not payload.allow_slug_update:
        raise SlugConflictError(document)

    if match.matched_by == "source_external_id" and document.slug != resolved_slug:
        slug_owner = await _get_document_by_slug(
            session,
            resolved_slug,
            workspace_id=workspace_id,
            exclude_id=document.id,
        )
        if slug_owner is not None:
            raise SlugConflictError(slug_owner)

    document.source_url = payload.source_url
    document.slug = resolved_slug
    document.title = payload.title
    document.language_code = payload.language_code
    document.doc_type = payload.doc_type
    document.status = payload.status
    document.visibility_scope = payload.visibility_scope
    document.owner_team = payload.owner_team
    document.meta = payload.metadata
    document.last_ingested_at = utcnow()
    await session.flush()
    return document


async def _get_current_revision(session: AsyncSession, document: Document) -> DocumentRevision | None:
    if document.current_revision_id is None:
        return None
    return await session.get(DocumentRevision, document.current_revision_id)


async def _create_revision(
    session: AsyncSession,
    *,
    document: Document,
    payload: IngestDocumentRequest,
    parsed: ParsedContent,
    checksum: str,
    content_hash: str,
) -> DocumentRevision:
    revision = DocumentRevision(
        document_id=document.id,
        revision_number=await _next_revision_number(session, document.id),
        source_revision_id=payload.source_revision_id,
        checksum=checksum,
        content_hash=content_hash,
        content_markdown=parsed.markdown_text,
        content_text=parsed.plain_text,
        content_tokens=TokenAwareChunker().count_tokens(parsed.plain_text),
        word_count=len(parsed.plain_text.split()),
    )
    session.add(revision)
    await session.flush()
    return revision



def _build_chunk_rows(
    *,
    document_id: UUID,
    revision_id: UUID,
    payload: IngestDocumentRequest,
    parsed: ParsedContent,
) -> list[dict[str, Any]]:
    chunker = TokenAwareChunker()
    chunk_content = parsed.markdown_text if payload.content_type == "markdown" and parsed.markdown_text else parsed.plain_text
    chunk_payloads = chunker.chunk(
        content_type=payload.content_type,
        content=chunk_content,
        metadata={
            "source_system": payload.source_system,
            "doc_type": payload.doc_type,
        },
    )
    if not chunk_payloads:
        chunk_payloads = chunker.chunk(content_type="text", content=parsed.plain_text)

    rows: list[dict[str, Any]] = []
    for chunk in chunk_payloads:
        rows.append(
            {
                "document_id": document_id,
                "revision_id": revision_id,
                "chunk_index": chunk.chunk_index,
                "heading_path": chunk.heading_path,
                "section_title": chunk.section_title,
                "content_text": normalize_whitespace(chunk.content_text),
                "content_tokens": chunk.content_tokens,
                "content_hash": chunk.content_hash,
                "metadata": chunk.metadata,
            }
        )
    return rows


async def _maybe_enqueue_incremental_glossary_refresh(session: AsyncSession, document: Document) -> None:
    if document.status != "published":
        return
    if document.source_system == "glossary":
        return
    from app.services.glossary import enqueue_glossary_refresh_job

    await enqueue_glossary_refresh_job(
        session,
        workspace_id=document.workspace_id,
        scope="incremental",
        target_document_id=document.id,
        priority=160,
    )


async def ingest_document(
    session: AsyncSession,
    payload: IngestDocumentRequest,
    *,
    workspace_id: UUID,
) -> IngestResult:
    parser = DocumentParser()
    parsed = parser.parse(content_type=payload.content_type, content=payload.content)

    resolved_slug = payload.slug or slugify(payload.title)
    checksum = sha256_text(payload.content)
    content_hash = sha256_text(parsed.plain_text)

    document = await _upsert_document(
        session,
        payload=payload,
        resolved_slug=resolved_slug,
        workspace_id=workspace_id,
    )
    current_revision = await _get_current_revision(session, document)

    if current_revision is not None and current_revision.checksum == checksum:
        await _maybe_enqueue_incremental_glossary_refresh(session, document)
        await session.commit()
        await session.refresh(document)
        return IngestResult(document=document, revision=current_revision, job=None, unchanged=True)

    revision = await _create_revision(
        session,
        document=document,
        payload=payload,
        parsed=parsed,
        checksum=checksum,
        content_hash=content_hash,
    )

    chunk_rows = _build_chunk_rows(
        document_id=document.id,
        revision_id=revision.id,
        payload=payload,
        parsed=parsed,
    )
    if chunk_rows:
        await session.execute(pg_insert(DocumentChunk), chunk_rows)

    await sync_document_links(
        session,
        document_id=document.id,
        revision_id=revision.id,
        markdown=parsed.markdown_text,
        workspace_id=workspace_id,
    )

    document.current_revision_id = revision.id
    document.updated_at = utcnow()
    document.last_ingested_at = utcnow()

    job = await create_embedding_job(
        session,
        document_id=document.id,
        revision_id=revision.id,
        priority=payload.priority,
    )
    await _maybe_enqueue_incremental_glossary_refresh(session, document)

    await session.commit()
    await session.refresh(document)
    await session.refresh(revision)
    await session.refresh(job)
    return IngestResult(document=document, revision=revision, job=job, unchanged=False)
