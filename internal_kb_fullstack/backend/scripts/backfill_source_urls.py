from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session_factory
from app.db.models import ConnectorConnection, ConnectorResource, ConnectorSourceItem, Document
from app.services.source_urls import canonicalize_source_url, connector_document_source_system


def canonical_document_source_url(document: Document) -> str | None:
    return canonicalize_source_url(
        source_system=document.source_system,
        source_url=document.source_url,
        source_external_id=document.source_external_id,
        slug=document.slug,
    )


def canonical_connector_item_source_url(
    item: ConnectorSourceItem,
    *,
    provider: str,
    selection_mode: str,
) -> str | None:
    return canonicalize_source_url(
        source_system=connector_document_source_system(provider, selection_mode=selection_mode),
        source_url=item.source_url,
        source_external_id=item.external_item_id,
        slug=item.name,
    )


async def backfill_document_source_urls_in_session(session: AsyncSession) -> int:
    updated = 0
    documents = list(
        (
            await session.execute(
                select(Document).where(Document.source_url.is_not(None))
            )
        ).scalars().all()
    )
    for document in documents:
        source_url = canonical_document_source_url(document)
        if source_url is None or source_url == document.source_url:
            continue
        document.source_url = source_url
        updated += 1
    return updated


async def backfill_document_source_urls() -> int:
    updated = 0
    async with get_session_factory()() as session:
        updated = await backfill_document_source_urls_in_session(session)
        if updated:
            await session.commit()
    return updated


async def backfill_connector_source_item_urls_in_session(session: AsyncSession) -> int:
    updated = 0
    rows = (
        await session.execute(
            select(
                ConnectorSourceItem,
                ConnectorConnection.provider,
                ConnectorResource.selection_mode,
            )
            .join(ConnectorConnection, ConnectorConnection.id == ConnectorSourceItem.connection_id)
            .join(ConnectorResource, ConnectorResource.id == ConnectorSourceItem.resource_id)
            .where(ConnectorSourceItem.source_url.is_not(None))
        )
    ).all()
    for item, provider, selection_mode in rows:
        source_url = canonical_connector_item_source_url(
            item,
            provider=str(provider),
            selection_mode=str(selection_mode),
        )
        if source_url is None or source_url == item.source_url:
            continue
        item.source_url = source_url
        updated += 1
    return updated


async def backfill_connector_source_item_urls() -> int:
    updated = 0
    async with get_session_factory()() as session:
        updated = await backfill_connector_source_item_urls_in_session(session)
        if updated:
            await session.commit()
    return updated


async def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize persisted source_url values into the https|generic contract.")
    _args = parser.parse_args()
    updated_documents = await backfill_document_source_urls()
    updated_connector_items = await backfill_connector_source_item_urls()
    print(
        json.dumps(
            {
                "event": "backfill_source_urls",
                "documents_updated": updated_documents,
                "connector_items_updated": updated_connector_items,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
