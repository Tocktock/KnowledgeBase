from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import documents as documents_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.documents import IngestDocumentRequest
from app.services.ingest import DocumentMatch, SlugConflictError, _upsert_document


class StubSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_calls = 0

    def add(self, item: object) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        self.flush_calls += 1


def make_payload(**overrides: object) -> IngestDocumentRequest:
    base = {
        "source_system": "manual",
        "title": "Transport",
        "slug": "transport",
        "content_type": "markdown",
        "content": "# Transport",
        "doc_type": "knowledge",
        "language_code": "ko",
        "status": "draft",
        "metadata": {},
    }
    base.update(overrides)
    return IngestDocumentRequest(**base)


def make_document(**overrides: object) -> SimpleNamespace:
    base = {
        "id": uuid4(),
        "source_system": "manual",
        "source_external_id": None,
        "source_url": None,
        "slug": "transport",
        "title": "Existing Transport",
        "language_code": "ko",
        "doc_type": "knowledge",
        "status": "published",
        "owner_team": "platform",
        "meta": {},
        "current_revision_id": None,
        "last_ingested_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_upsert_document_raises_slug_conflict_when_slug_updates_disallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = StubSession()
    existing = make_document()

    async def fake_find_document(_session: object, _payload: IngestDocumentRequest, _resolved_slug: str) -> DocumentMatch:
        return DocumentMatch(document=existing, matched_by="slug")

    monkeypatch.setattr("app.services.ingest._find_document", fake_find_document)

    with pytest.raises(SlugConflictError) as exc_info:
        await _upsert_document(session, payload=make_payload(allow_slug_update=False), resolved_slug="transport")

    assert exc_info.value.document is existing
    assert session.flush_calls == 0


@pytest.mark.asyncio
async def test_upsert_document_updates_existing_slug_when_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = StubSession()
    existing = make_document()
    fixed_now = datetime(2026, 3, 22, tzinfo=timezone.utc)

    async def fake_find_document(_session: object, _payload: IngestDocumentRequest, _resolved_slug: str) -> DocumentMatch:
        return DocumentMatch(document=existing, matched_by="slug")

    monkeypatch.setattr("app.services.ingest._find_document", fake_find_document)
    monkeypatch.setattr("app.services.ingest.utcnow", lambda: fixed_now)

    document = await _upsert_document(
        session,
        payload=make_payload(title="Transport Updated", owner_team="logistics", allow_slug_update=True),
        resolved_slug="transport",
    )

    assert document is existing
    assert document.title == "Transport Updated"
    assert document.owner_team == "logistics"
    assert document.last_ingested_at == fixed_now
    assert session.flush_calls == 1


@pytest.mark.asyncio
async def test_upsert_document_allows_source_external_id_match_even_when_slug_updates_disallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = StubSession()
    existing = make_document(source_external_id="source-123", slug="transport-old")

    async def fake_find_document(_session: object, _payload: IngestDocumentRequest, _resolved_slug: str) -> DocumentMatch:
        return DocumentMatch(document=existing, matched_by="source_external_id")

    async def fake_get_document_by_slug(_session: object, _slug: str, *, exclude_id: object = None) -> None:
        return None

    monkeypatch.setattr("app.services.ingest._find_document", fake_find_document)
    monkeypatch.setattr("app.services.ingest._get_document_by_slug", fake_get_document_by_slug)

    document = await _upsert_document(
        session,
        payload=make_payload(source_external_id="source-123", allow_slug_update=False),
        resolved_slug="transport",
    )

    assert document is existing
    assert document.slug == "transport"
    assert session.flush_calls == 1


@pytest.mark.asyncio
async def test_ingest_route_returns_structured_slug_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    conflict_document = make_document()

    async def override_session():
        yield object()

    async def fake_ingest_document(_session: object, _payload: IngestDocumentRequest):
        raise SlugConflictError(conflict_document)

    monkeypatch.setattr(documents_route, "ingest_document", fake_ingest_document)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/documents/ingest",
            json={
                "source_system": "manual",
                "title": "Transport",
                "slug": "transport",
                "content_type": "markdown",
                "content": "# Transport",
                "doc_type": "knowledge",
                "language_code": "ko",
                "status": "draft",
                "metadata": {},
                "allow_slug_update": False,
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "slug_conflict",
            "message": "A document with this slug already exists.",
            "document": {
                "id": str(conflict_document.id),
                "slug": "transport",
                "title": "Existing Transport",
                "status": "published",
                "owner_team": "platform",
            },
        }
    }
