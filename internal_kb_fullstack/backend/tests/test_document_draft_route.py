from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_authenticated_user
from app.api.routes import documents as documents_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.documents import DefinitionDraftReference, GenerateDefinitionDraftResponse
from app.services.auth import AuthenticatedUser
from app.services.document_drafts import DefinitionDraftGenerationError


def make_auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user=type("User", (), {"id": uuid4(), "email": "member@example.com", "name": "Member", "avatar_url": None})(),
        roles=["member"],
        current_workspace_id=uuid4(),
        current_workspace_slug="default",
        current_workspace_name="Default Workspace",
        current_workspace_role="member",
    )


@pytest.mark.asyncio
async def test_generate_definition_route_returns_generated_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user()

    async def fake_session() -> object:
        return object()

    async def override_session():
        yield await fake_session()

    async def fake_generate_definition_draft(_session: object, _payload: object) -> GenerateDefinitionDraftResponse:
        return GenerateDefinitionDraftResponse(
            title="Transport",
            slug="transport",
            query="Transport delivery operations",
            markdown=(
                "# Transport\n\n"
                "## Definition\n"
                "Transport is the shared term for shipment movement. [1]\n\n"
                "## How This Term Is Used Here\n"
                "The transport corpus uses the term for dispatch and tracking. [1]\n\n"
                "## Supporting Details\n"
                "- Teams coordinate shipment handoff. [1]\n\n"
                "## Open Questions\n"
                "- Which workflows need narrower definitions?\n\n"
                "## References\n\n"
                "1. [Transport Overview](/docs/transport-overview)"
            ),
            references=[
                DefinitionDraftReference(
                    index=1,
                    document_id=uuid4(),
                    document_title="Transport Overview",
                    document_slug="transport-overview",
                    source_system="notion-export",
                    source_url="https://example.com/transport-overview",
                    section_title="Definition",
                    heading_path=["Transport Overview"],
                    excerpt="Transport is the shared term for shipment movement.",
                )
            ],
        )

    monkeypatch.setattr(documents_route, "generate_definition_draft", fake_generate_definition_draft)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/documents/generate-definition",
            json={"topic": "Transport", "domain": "delivery operations"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Transport"
    assert payload["slug"] == "transport"
    assert payload["references"][0]["document_slug"] == "transport-overview"


@pytest.mark.asyncio
async def test_generate_definition_route_maps_generation_error_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user()

    async def override_session():
        yield object()

    async def fake_generate_definition_draft(_session: object, _payload: object) -> GenerateDefinitionDraftResponse:
        raise DefinitionDraftGenerationError("Draft cites references that do not exist: 9.")

    monkeypatch.setattr(documents_route, "generate_definition_draft", fake_generate_definition_draft)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/documents/generate-definition",
            json={"topic": "Transport"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Draft cites references that do not exist: 9."


@pytest.mark.asyncio
async def test_generate_definition_route_requires_authentication() -> None:
    async def override_session():
        yield object()

    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/documents/generate-definition",
            json={"topic": "Transport"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."
