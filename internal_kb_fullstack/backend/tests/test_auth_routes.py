from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_authenticated_user
from app.api.routes import auth as auth_route
from app.db.models import ConnectorOAuthPurpose, ConnectorOAuthState, User
from app.db.engine import get_db_session
from app.main import app
from app.schemas.auth import (
    AuthCallbackResponse,
    AuthMeResponse,
    AuthSessionResponse,
    PasswordResetLinkCreateResponse,
    PasswordResetPreviewResponse,
)
from app.schemas.workspace import WorkspaceSummary
from app.services import auth as auth_service
from app.services.auth import (
    AuthForbiddenError,
    AuthenticatedUser,
    WorkspaceContext,
    complete_google_login,
    future_utc,
    start_google_login,
)


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


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeAuthSession:
    def __init__(self, *, state_row: ConnectorOAuthState | None = None, existing_user: User | None = None):
        self.state_row = state_row
        self.existing_user = existing_user
        self.added: list[object] = []
        self.deleted_state_id = None
        self.committed = False
        self.flushed = False

    def add(self, obj: object) -> None:
        self.added.append(obj)
        if isinstance(obj, User):
            self.existing_user = obj

    async def execute(self, statement):
        descriptions = getattr(statement, "column_descriptions", None)
        if descriptions:
            entity = descriptions[0].get("entity")
            if entity is ConnectorOAuthState:
                return FakeScalarResult(self.state_row)
            if entity is User:
                return FakeScalarResult(self.existing_user)
        table = getattr(statement, "table", None)
        if table is not None and getattr(table, "name", None) == ConnectorOAuthState.__tablename__:
            self.deleted_state_id = self.state_row.id if self.state_row is not None else None
            return FakeScalarResult(None)
        raise AssertionError(f"Unexpected statement: {statement!s}")

    async def flush(self) -> None:
        self.flushed = True
        if self.existing_user is not None and self.existing_user.id is None:
            self.existing_user.id = uuid4()

    async def commit(self) -> None:
        self.committed = True


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
async def test_password_invite_signup_route_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_invite_signup(_session: object, payload) -> AuthSessionResponse:
        captured["invite_token"] = payload.invite_token
        captured["name"] = payload.name
        return make_auth_session_response()

    monkeypatch.setattr(auth_route, "invite_signup_with_password", fake_invite_signup)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/auth/password/invite-signup",
            json={
                "invite_token": "invite-xyz",
                "name": "Invited Member",
                "password": "hunter2-hunter2",
                "return_to": "/search",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "invite_token": "invite-xyz",
        "name": "Invited Member",
    }
    assert response.json()["redirect_to"] == "/connectors"


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
async def test_auth_me_route_returns_authenticated_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_get_auth_me(_session: object, session_token: str | None) -> AuthMeResponse:
        assert session_token == "session-token"
        return AuthMeResponse(authenticated=True, user=make_auth_session_response().user)

    monkeypatch.setattr(auth_route, "get_auth_me", fake_get_auth_me)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/auth/me", headers={"x-kb-session": "session-token"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["user"]["email"] == "member@example.com"


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
async def test_logout_route_returns_ok_and_passes_session_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | None] = {}

    async def override_session():
        yield object()

    async def fake_logout_session(_session: object, session_token: str | None) -> None:
        captured["session_token"] = session_token

    monkeypatch.setattr(auth_route, "logout_session", fake_logout_session)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/auth/logout", headers={"x-kb-session": "session-token"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured == {"session_token": "session-token"}


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


@pytest.mark.asyncio
async def test_start_google_login_uses_redirect_override(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeAuthSession()
    monkeypatch.setattr(
        auth_service,
        "get_settings",
        lambda: SimpleNamespace(
            app_public_url="http://localhost:3000",
            google_oauth_client_id="client-id",
            google_oauth_client_secret="client-secret",
            google_oauth_redirect_uri="https://auth.example.com/google/callback",
            oauth_state_ttl_seconds=600,
        ),
    )

    response = await start_google_login(session, return_path="/search")

    assert "redirect_uri=https%3A%2F%2Fauth.example.com%2Fgoogle%2Fcallback" in response.authorization_url
    assert session.committed is True
    assert session.added and isinstance(session.added[0], ConnectorOAuthState)


@pytest.mark.asyncio
async def test_complete_google_login_returns_callback_response_without_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_row = ConnectorOAuthState(
        id=uuid4(),
        state="oauth-state",
        purpose=ConnectorOAuthPurpose.login.value,
        workspace_id=None,
        owner_scope="personal",
        owner_user_id=None,
        code_verifier="code-verifier",
        return_path="/connectors",
        expires_at=future_utc(seconds=600),
    )
    session = FakeAuthSession(state_row=state_row)
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        auth_service,
        "get_settings",
        lambda: SimpleNamespace(
            app_public_url="http://localhost:3000",
            google_oauth_client_id="client-id",
            google_oauth_client_secret="client-secret",
            google_oauth_redirect_uri="https://auth.example.com/google/callback",
            admin_emails=set(),
        ),
    )

    async def fake_google_token_exchange(*, code: str, code_verifier: str, redirect_uri: str) -> dict[str, str]:
        captured["code"] = code
        captured["code_verifier"] = code_verifier
        captured["redirect_uri"] = redirect_uri
        return {"access_token": "token"}

    async def fake_google_userinfo(_access_token: str) -> dict[str, str]:
        return {
            "sub": "google-subject",
            "email": "member@example.com",
            "name": "Member",
            "picture": "https://example.com/avatar.png",
        }

    async def fake_get_user_by_email(_session, _email: str):
        return None

    async def fake_create_user_session(_session, user: User):
        return (
            "session-token",
            ["member"],
            WorkspaceContext(
                workspace=SimpleNamespace(id=uuid4(), slug="default", name="Default Workspace", is_default=True),
                role="member",
            ),
        )

    monkeypatch.setattr(auth_service, "_google_token_exchange", fake_google_token_exchange)
    monkeypatch.setattr(auth_service, "_google_userinfo", fake_google_userinfo)
    monkeypatch.setattr(auth_service, "_get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_service, "_create_user_session", fake_create_user_session)

    response = await complete_google_login(session, state="oauth-state", code="google-code")

    assert isinstance(response, AuthCallbackResponse)
    assert response.session_token == "session-token"
    assert response.redirect_to == "/connectors"
    assert response.user.email == "member@example.com"
    assert captured == {
        "code": "google-code",
        "code_verifier": "code-verifier",
        "redirect_uri": "https://auth.example.com/google/callback",
    }
    assert session.committed is True
    assert session.deleted_state_id == state_row.id
