from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import documents as documents_route
from app.db.engine import get_db_session
from app.main import app


def make_document_row(*, doc_type: str = "knowledge") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "source_system": "manual",
        "source_external_id": None,
        "source_url": None,
        "slug": f"doc-{doc_type}",
        "title": f"{doc_type} doc",
        "language_code": "ko",
        "doc_type": doc_type,
        "status": "published",
        "visibility_scope": "member_visible",
        "owner_team": "product",
        "metadata": {},
        "current_revision_id": None,
        "created_at": now,
        "updated_at": now,
        "last_ingested_at": None,
        "revision_number": 1,
        "word_count": 100,
        "content_tokens": 120,
        "excerpt": "example excerpt",
    }


@pytest.mark.asyncio
async def test_list_documents_route_accepts_single_doc_type(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_list_documents(
        _session: object,
        *,
        q: str | None = None,
        owner_team: str | None = None,
        doc_types: list[str] | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        captured.update(
            {
                "q": q,
                "owner_team": owner_team,
                "doc_types": doc_types,
                "status": status,
                "limit": limit,
                "offset": offset,
            }
        )
        return [make_document_row(doc_type=doc_types[0] if doc_types else "knowledge")], 1

    monkeypatch.setattr(documents_route, "list_documents", fake_list_documents)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/documents", params={"doc_type": "knowledge"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["doc_types"] == ["knowledge"]
    assert response.json()["items"][0]["doc_type"] == "knowledge"


@pytest.mark.asyncio
async def test_list_documents_route_accepts_multiple_doc_types(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_list_documents(
        _session: object,
        *,
        q: str | None = None,
        owner_team: str | None = None,
        doc_types: list[str] | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        captured.update(
            {
                "q": q,
                "owner_team": owner_team,
                "doc_types": doc_types,
                "status": status,
                "limit": limit,
                "offset": offset,
            }
        )
        return [make_document_row(doc_type="runbook"), make_document_row(doc_type="spec")], 2

    monkeypatch.setattr(documents_route, "list_documents", fake_list_documents)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/documents",
            params=[("doc_type", "runbook"), ("doc_type", "spec"), ("limit", "40")],
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["doc_types"] == ["runbook", "spec"]
    assert captured["limit"] == 40
    assert [item["doc_type"] for item in response.json()["items"]] == ["runbook", "spec"]
