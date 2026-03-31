from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_optional_authenticated_user
from app.api.routes import documents as documents_route
from app.db.engine import get_db_session
from app.main import app
from app.services.auth import AuthenticatedUser


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


def make_auth_user(*, workspace_id=None, role: str = "owner") -> AuthenticatedUser:
    return AuthenticatedUser(
        user=SimpleNamespace(id=uuid4(), email="owner@example.com", name="Owner", avatar_url=None),
        roles=["member"],
        current_workspace_id=workspace_id or uuid4(),
        current_workspace_slug="default",
        current_workspace_name="Default Workspace",
        current_workspace_role=role,
    )


def make_document_namespace(*, visibility_scope: str = "member_visible"):
    now = datetime.now(timezone.utc)
    document_id = uuid4()
    revision_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        source_system="manual",
        source_external_id=None,
        source_url=None,
        slug="evidence-doc",
        title="Evidence doc",
        language_code="ko",
        doc_type="knowledge",
        status="published",
        visibility_scope=visibility_scope,
        owner_team="product",
        meta={},
        current_revision_id=revision_id,
        created_at=now,
        updated_at=now,
        last_ingested_at=None,
    )
    revision = SimpleNamespace(
        id=revision_id,
        document_id=document_id,
        revision_number=1,
        source_revision_id=None,
        checksum="checksum",
        content_hash="content-hash",
        content_markdown="# Evidence",
        content_text="Evidence",
        content_tokens=10,
        word_count=2,
        created_at=now,
    )
    return document, revision


@pytest.mark.asyncio
async def test_list_documents_route_accepts_single_doc_type(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_list_documents(
        _session: object,
        *,
        workspace_id: object = None,
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
                "workspace_id": workspace_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return [make_document_row(doc_type=doc_types[0] if doc_types else "knowledge")], 1

    monkeypatch.setattr(documents_route, "list_documents", fake_list_documents)
    async def fake_resolve_read_workspace_id(*_args, **_kwargs):
        return None

    monkeypatch.setattr(documents_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/documents", params={"doc_type": "knowledge"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["workspace_id"] is None
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
        workspace_id: object = None,
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
                "workspace_id": workspace_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return [make_document_row(doc_type="runbook"), make_document_row(doc_type="spec")], 2

    monkeypatch.setattr(documents_route, "list_documents", fake_list_documents)
    async def fake_resolve_read_workspace_id(*_args, **_kwargs):
        return None

    monkeypatch.setattr(documents_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/documents",
            params=[("doc_type", "runbook"), ("doc_type", "spec"), ("limit", "40")],
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["workspace_id"] is None
    assert captured["doc_types"] == ["runbook", "spec"]
    assert captured["limit"] == 40
    assert [item["doc_type"] for item in response.json()["items"]] == ["runbook", "spec"]


@pytest.mark.asyncio
async def test_get_document_by_slug_route_hides_evidence_only_for_member(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    auth_user = make_auth_user(workspace_id=workspace_id, role="member")
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_resolve_read_workspace_id(*_args, **_kwargs):
        return workspace_id

    async def fake_get_document_by_slug(_session: object, *, slug: str, workspace_id=None, include_evidence_only: bool = False):
        captured.update(
            {
                "slug": slug,
                "workspace_id": workspace_id,
                "include_evidence_only": include_evidence_only,
            }
        )
        return None, None

    monkeypatch.setattr(documents_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    monkeypatch.setattr(documents_route, "get_document_by_slug", fake_get_document_by_slug)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/documents/slug/evidence-doc")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert captured["include_evidence_only"] is False


@pytest.mark.asyncio
async def test_get_document_route_allows_evidence_only_for_workspace_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    auth_user = make_auth_user(workspace_id=workspace_id, role="owner")
    document, revision = make_document_namespace(visibility_scope="evidence_only")
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_resolve_read_workspace_id(*_args, **_kwargs):
        return workspace_id

    async def fake_get_document_detail(_session: object, document_id, *, workspace_id=None, include_evidence_only: bool = False):
        captured.update(
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "include_evidence_only": include_evidence_only,
            }
        )
        return document, revision, []

    monkeypatch.setattr(documents_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    monkeypatch.setattr(documents_route, "get_document_detail", fake_get_document_detail)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/documents/{document.id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["document"]["visibility_scope"] == "evidence_only"
    assert captured["include_evidence_only"] is True


@pytest.mark.asyncio
async def test_get_document_content_route_hides_evidence_only_for_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_resolve_read_workspace_id(*_args, **_kwargs):
        return workspace_id

    async def fake_get_document_detail(_session: object, document_id, *, workspace_id=None, include_evidence_only: bool = False):
        captured.update(
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "include_evidence_only": include_evidence_only,
            }
        )
        return None, None, []

    monkeypatch.setattr(documents_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    monkeypatch.setattr(documents_route, "get_document_detail", fake_get_document_detail)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = lambda: None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/documents/{uuid4()}/content")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert captured["include_evidence_only"] is False


@pytest.mark.asyncio
async def test_get_document_relations_route_passes_admin_evidence_access(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    auth_user = make_auth_user(workspace_id=workspace_id, role="admin")
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_resolve_read_workspace_id(*_args, **_kwargs):
        return workspace_id

    async def fake_get_document_relations(
        _session: object,
        *,
        document_id,
        workspace_id=None,
        limit: int = 8,
        include_evidence_only: bool = False,
    ):
        captured.update(
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "limit": limit,
                "include_evidence_only": include_evidence_only,
            }
        )
        return {"outgoing": [], "backlinks": [], "related": []}

    monkeypatch.setattr(documents_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    monkeypatch.setattr(documents_route, "get_document_relations", fake_get_document_relations)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/documents/{uuid4()}/relations")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["include_evidence_only"] is True
