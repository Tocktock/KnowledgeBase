from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.utils import heading_anchor, slugify
from app.db.models import Document, DocumentLink, DocumentRevision
from app.services.catalog import find_related_documents, lookup_documents_by_slugs

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]")
DOCS_LINK_RE = re.compile(r"\[([^\]]+)\]\(/docs/([a-zA-Z0-9\-_/]+)(?:#([^)\s?]+))?(?:\?[^)]*)?\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


@dataclass(slots=True)
class InternalLink:
    target_slug: str
    target_anchor: str | None
    link_text: str | None
    raw_target: str



def extract_internal_links(markdown: str) -> list[InternalLink]:
    if not markdown:
        return []

    links: list[InternalLink] = []
    for match in WIKI_LINK_RE.finditer(markdown):
        raw_target = match.group(1).strip()
        slug = slugify(raw_target)
        if not slug:
            continue
        links.append(
            InternalLink(
                target_slug=slug,
                target_anchor=match.group(2).strip() if match.group(2) else None,
                link_text=match.group(3).strip() if match.group(3) else raw_target,
                raw_target=raw_target,
            )
        )

    for match in DOCS_LINK_RE.finditer(markdown):
        raw_target = match.group(2).strip()
        slug = slugify(raw_target)
        if not slug:
            continue
        links.append(
            InternalLink(
                target_slug=slug,
                target_anchor=match.group(3).strip() if match.group(3) else None,
                link_text=match.group(1).strip() if match.group(1) else raw_target,
                raw_target=raw_target,
            )
        )

    return links



def extract_internal_slugs(markdown: str) -> list[str]:
    slugs = [link.target_slug for link in extract_internal_links(markdown)]
    return list(dict.fromkeys(slugs))



def extract_heading_items(markdown: str | None) -> list[dict[str, str]]:
    if not markdown:
        return []

    headings: list[dict[str, str]] = []
    for match in HEADING_RE.finditer(markdown):
        title = match.group(1).strip()
        if not title:
            continue
        headings.append({"title": title, "id": heading_anchor(title)})
    return headings


async def sync_document_links(
    session: AsyncSession,
    *,
    document_id: UUID,
    revision_id: UUID,
    markdown: str | None,
) -> None:
    await session.execute(delete(DocumentLink).where(DocumentLink.source_revision_id == revision_id))

    links = extract_internal_links(markdown or "")
    if not links:
        return

    target_slugs = list(dict.fromkeys(link.target_slug for link in links))
    existing_rows = await session.execute(select(Document.id, Document.slug).where(Document.slug.in_(target_slugs)))
    target_by_slug = {row.slug: row.id for row in existing_rows}

    rows = [
        {
            "source_document_id": document_id,
            "source_revision_id": revision_id,
            "target_slug": link.target_slug,
            "target_document_id": target_by_slug.get(link.target_slug),
            "link_text": link.link_text,
            "link_anchor": link.target_anchor,
            "link_order": index,
        }
        for index, link in enumerate(links)
    ]
    await session.execute(pg_insert(DocumentLink), rows)


async def get_document_relations(
    session: AsyncSession,
    *,
    document_id: UUID,
    limit: int = 8,
) -> dict[str, list[dict]]:
    document = await session.get(Document, document_id)
    if document is None:
        return {"outgoing": [], "backlinks": [], "related": []}

    revision = None
    if document.current_revision_id is not None:
        revision = await session.get(DocumentRevision, document.current_revision_id)

    outgoing_slugs: list[str] = []
    if revision is not None:
        result = await session.execute(
            select(DocumentLink.target_slug)
            .where(DocumentLink.source_revision_id == revision.id)
            .order_by(DocumentLink.link_order.asc())
        )
        outgoing_slugs = list(dict.fromkeys(result.scalars().all()))

    outgoing = await lookup_documents_by_slugs(session, outgoing_slugs, exclude_id=document.id)
    backlinks = await find_backlinks(session, target_document_id=document.id, target_slug=document.slug, exclude_id=document.id, limit=limit)
    related = await find_related_documents(
        session,
        title=document.title,
        owner_team=document.owner_team,
        exclude_id=document.id,
        limit=limit,
    )

    return {
        "outgoing": outgoing[:limit],
        "backlinks": backlinks[:limit],
        "related": related[:limit],
    }


async def find_backlinks(
    session: AsyncSession,
    *,
    target_document_id: UUID,
    target_slug: str,
    exclude_id: UUID,
    limit: int,
) -> list[dict]:
    current_revision = aliased(DocumentRevision)

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
        .join(DocumentLink, DocumentLink.source_revision_id == current_revision.id)
        .where(
            Document.id != exclude_id,
            Document.status == "published",
            or_(
                DocumentLink.target_document_id == target_document_id,
                DocumentLink.target_slug == target_slug,
            ),
        )
        .group_by(
            Document.id,
            Document.slug,
            Document.title,
            current_revision.content_text,
            Document.owner_team,
            Document.doc_type,
            Document.updated_at,
        )
        .order_by(Document.updated_at.desc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]
