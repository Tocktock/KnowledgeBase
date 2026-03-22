from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.models import Document
from app.services import glossary as glossary_service
from app.services.ingest import _maybe_enqueue_incremental_glossary_refresh


def make_document(*, status: str, source_system: str) -> Document:
    return Document(
        id=uuid4(),
        source_system=source_system,
        source_external_id=None,
        source_url=None,
        slug=f"doc-{uuid4()}",
        title="Test",
        language_code="ko",
        doc_type="knowledge",
        status=status,
        owner_team="product",
        meta={},
        current_revision_id=None,
    )


@pytest.mark.asyncio
async def test_enqueue_incremental_glossary_refresh_for_published_non_glossary_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object, int]] = []

    async def fake_enqueue(_session: object, *, scope: str, target_document_id: object, priority: int):
        calls.append((scope, target_document_id, priority))
        return None

    monkeypatch.setattr(glossary_service, "enqueue_glossary_refresh_job", fake_enqueue)

    document = make_document(status="published", source_system="manual")
    await _maybe_enqueue_incremental_glossary_refresh(object(), document)

    assert calls == [("incremental", document.id, 160)]


@pytest.mark.asyncio
async def test_skip_incremental_glossary_refresh_for_draft_or_glossary_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object, int]] = []

    async def fake_enqueue(_session: object, *, scope: str, target_document_id: object, priority: int):
        calls.append((scope, target_document_id, priority))
        return None

    monkeypatch.setattr(glossary_service, "enqueue_glossary_refresh_job", fake_enqueue)

    await _maybe_enqueue_incremental_glossary_refresh(object(), make_document(status="draft", source_system="manual"))
    await _maybe_enqueue_incremental_glossary_refresh(object(), make_document(status="published", source_system="glossary"))

    assert calls == []
