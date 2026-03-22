from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models import Document, DocumentChunk, DocumentRevision


async def list_documents(
    session: AsyncSession,
    *,
    q: str | None = None,
    owner_team: str | None = None,
    doc_types: Iterable[str] | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    current_revision = aliased(DocumentRevision)
    normalized_doc_types = tuple(dict.fromkeys(doc_type for doc_type in (doc_types or []) if doc_type))

    filters = []
    if q:
        q_like = f"%{q}%"
        filters.append(
            or_(
                Document.title.ilike(q_like),
                Document.slug.ilike(q_like),
                current_revision.content_text.ilike(q_like),
            )
        )
    if owner_team:
        filters.append(Document.owner_team == owner_team)
    if normalized_doc_types:
        filters.append(Document.doc_type.in_(normalized_doc_types))
    if status:
        filters.append(Document.status == status)

    stmt = (
        select(
            Document.id,
            Document.source_system,
            Document.source_external_id,
            Document.source_url,
            Document.slug,
            Document.title,
            Document.language_code,
            Document.doc_type,
            Document.status,
            Document.owner_team,
            Document.meta.label("metadata"),
            Document.current_revision_id,
            Document.created_at,
            Document.updated_at,
            Document.last_ingested_at,
            current_revision.revision_number,
            current_revision.word_count,
            current_revision.content_tokens,
            func.left(current_revision.content_text, 240).label("excerpt"),
        )
        .select_from(Document)
        .outerjoin(current_revision, current_revision.id == Document.current_revision_id)
        .where(*filters)
        .order_by(Document.updated_at.desc(), Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    count_stmt = (
        select(func.count(Document.id))
        .select_from(Document)
        .outerjoin(current_revision, current_revision.id == Document.current_revision_id)
        .where(*filters)
    )

    rows = (await session.execute(stmt)).mappings().all()
    total = int((await session.execute(count_stmt)).scalar_one())
    return [dict(row) for row in rows], total


async def get_document_by_slug(
    session: AsyncSession,
    *,
    slug: str,
) -> tuple[Document | None, DocumentRevision | None]:
    result = await session.execute(select(Document).where(Document.slug == slug))
    document = result.scalar_one_or_none()
    if document is None:
        return None, None

    revision = None
    if document.current_revision_id is not None:
        revision = await session.get(DocumentRevision, document.current_revision_id)
    return document, revision


async def get_document_detail(
    session: AsyncSession,
    document_id: UUID,
) -> tuple[Document | None, DocumentRevision | None, list[DocumentChunk]]:
    document = await session.get(Document, document_id)
    if document is None:
        return None, None, []

    revision = None
    if document.current_revision_id is not None:
        revision = await session.get(DocumentRevision, document.current_revision_id)

    chunks: list[DocumentChunk] = []
    if revision is not None:
        result = await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.revision_id == revision.id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        chunks = list(result.scalars().all())

    return document, revision, chunks


async def lookup_documents_by_slugs(
    session: AsyncSession,
    slugs: Iterable[str],
    *,
    exclude_id: UUID | None = None,
) -> list[dict]:
    normalized = list(dict.fromkeys(slug.strip().lower() for slug in slugs if slug.strip()))
    if not normalized:
        return []

    current_revision = aliased(DocumentRevision)
    ordering = case({slug: index for index, slug in enumerate(normalized)}, value=Document.slug, else_=len(normalized))
    stmt = (
        select(
            Document.id,
            Document.slug,
            Document.title,
            func.left(current_revision.content_text, 180).label("excerpt"),
            Document.owner_team,
            Document.doc_type,
            Document.updated_at,
        )
        .join(current_revision, current_revision.id == Document.current_revision_id)
        .where(Document.slug.in_(normalized))
    )
    if exclude_id is not None:
        stmt = stmt.where(Document.id != exclude_id)

    rows = (await session.execute(stmt.order_by(ordering.asc(), Document.updated_at.desc()))).mappings().all()
    return [dict(row) for row in rows]


async def find_related_documents(
    session: AsyncSession,
    *,
    title: str,
    owner_team: str | None,
    exclude_id: UUID,
    limit: int,
) -> list[dict]:
    current_revision = aliased(DocumentRevision)
    score = func.similarity(Document.title, title) + case(
        (Document.owner_team == owner_team, literal(0.15)),
        else_=literal(0.0),
    )

    stmt = (
        select(
            Document.id,
            Document.slug,
            Document.title,
            func.left(current_revision.content_text, 180).label("excerpt"),
            Document.owner_team,
            Document.doc_type,
            Document.updated_at,
            score.label("score"),
        )
        .join(current_revision, current_revision.id == Document.current_revision_id)
        .where(Document.id != exclude_id, Document.status == "published")
        .order_by(score.desc(), Document.updated_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]
