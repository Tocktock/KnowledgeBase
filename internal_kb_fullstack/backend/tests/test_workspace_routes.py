from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_authenticated_user
from app.api.routes import workspace as workspace_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.workspace import (
    WorkspaceContextResponse,
    WorkspaceInvitationAcceptResponse,
    WorkspaceInvitationCreateResponse,
    WorkspaceInvitationPreviewResponse,
    WorkspaceInvitationSummary,
    WorkspaceOverviewResponse,
    WorkspaceSummary,
)
from app.services.auth import AuthenticatedUser
from app.services.workspace import WorkspaceForbiddenError


def make_auth_user(*, role: str = "owner") -> AuthenticatedUser:
    return AuthenticatedUser(
        user=SimpleNamespace(id=uuid4(), email="owner@example.com", name="Owner", avatar_url=None),
        roles=["member"],
        current_workspace_id=uuid4(),
        current_workspace_slug="default",
        current_workspace_name="Default Workspace",
        current_workspace_role=role,
    )


@pytest.mark.asyncio
async def test_get_workspace_route_returns_workspace_context(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="admin")

    async def fake_get_current_workspace(_auth_user: AuthenticatedUser) -> WorkspaceContextResponse:
        assert _auth_user.current_workspace_id == auth_user.current_workspace_id
        return WorkspaceContextResponse(
            workspace=WorkspaceSummary(
                id=auth_user.current_workspace_id,
                slug="default",
                name="Default Workspace",
                is_default=True,
            ),
            role="admin",
            can_manage_connectors=True,
        )

    monkeypatch.setattr(workspace_route, "get_current_workspace", fake_get_current_workspace)
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/workspace")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["workspace"]["name"] == "Default Workspace"
    assert response.json()["role"] == "admin"
    assert response.json()["can_manage_connectors"] is True


@pytest.mark.asyncio
async def test_get_workspace_overview_route_supports_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_get_workspace_overview(_session: object, _auth_user: object | None) -> WorkspaceOverviewResponse:
        assert _auth_user is None
        return WorkspaceOverviewResponse(
            authenticated=False,
            setup_state="anonymous",
            next_actions=["Sign in to connect workspace sources."],
            featured_docs=[],
            featured_concepts=[],
            recent_sync_issues=[],
        )

    monkeypatch.setattr(workspace_route, "get_workspace_overview", fake_get_workspace_overview)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/workspace/overview")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert response.json()["setup_state"] == "anonymous"


@pytest.mark.asyncio
async def test_create_workspace_invitation_route_returns_invite_link(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="owner")
    invitation_id = uuid4()

    async def override_session():
        yield object()

    async def fake_create_workspace_invitation(_session: object, _auth_user: AuthenticatedUser, payload):
        assert payload.invited_email == "member@example.com"
        assert payload.role == "member"
        assert _auth_user.user.email == auth_user.user.email
        return WorkspaceInvitationCreateResponse(
            invitation=WorkspaceInvitationSummary(
                id=invitation_id,
                workspace_id=auth_user.current_workspace_id,
                invited_email="member@example.com",
                role="member",
                expires_at=datetime.now(timezone.utc),
                accepted_at=None,
                created_at=datetime.now(timezone.utc),
            ),
            invite_url="http://localhost:3000/invite/token-123",
        )

    monkeypatch.setattr(workspace_route, "create_workspace_invitation", fake_create_workspace_invitation)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workspace/invitations",
            json={"invited_email": "member@example.com", "role": "member"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["invite_url"] == "http://localhost:3000/invite/token-123"


@pytest.mark.asyncio
async def test_preview_workspace_invitation_route_allows_anonymous_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()

    async def override_session():
        yield object()

    async def fake_preview_workspace_invitation(_session: object, *, invitation_token: str) -> WorkspaceInvitationPreviewResponse:
        assert invitation_token == "token-123"
        return WorkspaceInvitationPreviewResponse(
            invited_email="member@example.com",
            workspace=WorkspaceSummary(
                id=workspace_id,
                slug="default",
                name="Default Workspace",
                is_default=True,
            ),
            role="member",
            expires_at=datetime.now(timezone.utc),
            accepted_at=None,
            is_expired=False,
            local_password_exists=False,
        )

    monkeypatch.setattr(workspace_route, "preview_workspace_invitation", fake_preview_workspace_invitation)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/workspace/invitations/token-123/preview")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["invited_email"] == "member@example.com"
    assert response.json()["workspace"]["name"] == "Default Workspace"


@pytest.mark.asyncio
async def test_create_workspace_invitation_route_rejects_member(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")

    async def override_session():
        yield object()

    async def fake_create_workspace_invitation(_session: object, _auth_user: AuthenticatedUser, payload):
        raise WorkspaceForbiddenError("Workspace admin permission required.")

    monkeypatch.setattr(workspace_route, "create_workspace_invitation", fake_create_workspace_invitation)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workspace/invitations",
            json={"invited_email": "member@example.com", "role": "member"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Workspace admin permission required."}


@pytest.mark.asyncio
async def test_accept_workspace_invitation_route_passes_session_token(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")
    captured: dict[str, str | None] = {}

    async def override_session():
        yield object()

    async def fake_accept_workspace_invitation(
        _session: object,
        _auth_user: AuthenticatedUser,
        *,
        invitation_token: str,
        session_token: str | None,
    ) -> WorkspaceInvitationAcceptResponse:
        captured["invitation_token"] = invitation_token
        captured["session_token"] = session_token
        return WorkspaceInvitationAcceptResponse(
            workspace=WorkspaceSummary(
                id=auth_user.current_workspace_id,
                slug="default",
                name="Default Workspace",
                is_default=True,
            ),
            role="member",
        )

    monkeypatch.setattr(workspace_route, "accept_workspace_invitation", fake_accept_workspace_invitation)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workspace/invitations/token-abc/accept",
            headers={"X-KB-Session": "session-token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "invitation_token": "token-abc",
        "session_token": "session-token",
    }


@pytest.mark.asyncio
async def test_accept_workspace_invitation_route_rejects_email_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")

    async def override_session():
        yield object()

    async def fake_accept_workspace_invitation(
        _session: object,
        _auth_user: AuthenticatedUser,
        *,
        invitation_token: str,
        session_token: str | None,
    ) -> WorkspaceInvitationAcceptResponse:
        raise WorkspaceForbiddenError("Workspace invitation email does not match the signed-in user.")

    monkeypatch.setattr(workspace_route, "accept_workspace_invitation", fake_accept_workspace_invitation)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workspace/invitations/token-abc/accept",
            headers={"X-KB-Session": "session-token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Workspace invitation email does not match the signed-in user."}
