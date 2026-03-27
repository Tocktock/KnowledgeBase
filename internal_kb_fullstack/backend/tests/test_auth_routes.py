from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_authenticated_user
from app.api.routes import auth as auth_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.auth import (
    AuthSessionResponse,
    PasswordResetLinkCreateResponse,
    PasswordResetPreviewResponse,
)
from app.schemas.workspace import WorkspaceSummary
from app.services.auth import AuthForbiddenError, AuthenticatedUser


def make_auth_user(*, role: str = "owner") -> AuthenticatedUser:
    return AuthenticatedUser(
        user=SimpleNamespace(id=uuid4(), email="owner@example.com", name="Owner", avatar_url=None),
        roles=["member"],
        current_workspace_id=uuid4(),
        current_workspace_slug="default",
        current_workspace_name="Default Workspace",
        current_workspace_role=role,
    )


def make_auth_session_response() -> AuthSessionResponse:
    return AuthSessionResponse(
        session_token="session-token",
        redirect_to="/connectors",
        user={
            "id": str(uuid4()),
            "email": "member@example.com",
            "name": "Member",
            "avatar_url": None,
            "roles": ["member"],
            "is_admin": False,
            "last_login_at": None,
            "current_workspace": WorkspaceSummary(
                id=uuid4(),
                slug="default",
                name="Default Workspace",
                is_default=True,
            ),
            "current_workspace_role": "member",
            "can_manage_workspace_connectors": False,
        },
    )


@pytest.mark.asyncio
async def test_password_login_route_passes_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_password_login(_session: object, payload) -> AuthSessionResponse:
        captured["email"] = payload.email
        captured["invite_token"] = payload.invite_token
        return make_auth_session_response()

    monkeypatch.setattr(auth_route, "password_login", fake_password_login)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/auth/password/login",
            json={
                "email": "member@example.com",
                "password": "hunter2-hunter2",
                "invite_token": "invite-123",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "email": "member@example.com",
        "invite_token": "invite-123",
    }
    assert response.json()["session_token"] == "session-token"


@pytest.mark.asyncio
async def test_password_reset_link_route_requires_workspace_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")

    async def override_session():
        yield object()

    async def fake_create_password_reset_link(_session: object, _auth_user: AuthenticatedUser, _payload):
        raise AuthForbiddenError("Workspace admin permission required.")

    monkeypatch.setattr(auth_route, "create_password_reset_link", fake_create_password_reset_link)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/auth/password/reset-links", json={"email": "member@example.com"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Workspace admin permission required."}


@pytest.mark.asyncio
async def test_password_reset_preview_route_is_public(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_preview_password_reset(_session: object, *, token: str) -> PasswordResetPreviewResponse:
        assert token == "reset-123"
        return PasswordResetPreviewResponse(
            email="member@example.com",
            name="Member",
            expires_at=datetime.now(timezone.utc),
            used_at=None,
            is_expired=False,
        )

    monkeypatch.setattr(auth_route, "preview_password_reset", fake_preview_password_reset)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/auth/password/reset/reset-123")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["email"] == "member@example.com"


@pytest.mark.asyncio
async def test_password_reset_consume_route_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_consume_password_reset(_session: object, *, token: str, payload) -> AuthSessionResponse:
        assert token == "reset-abc"
        assert payload.password == "new-password-123"
        return make_auth_session_response()

    monkeypatch.setattr(auth_route, "consume_password_reset", fake_consume_password_reset)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/auth/password/reset/reset-abc",
            json={"password": "new-password-123"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["redirect_to"] == "/connectors"
