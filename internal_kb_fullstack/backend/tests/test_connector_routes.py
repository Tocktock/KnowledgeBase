from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_optional_authenticated_user
from app.api.routes import auth as auth_route
from app.api.routes import connectors as connectors_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.auth import OAuthStartResponse
from app.schemas.connectors import ConnectorReadinessResponse
from app.services.connectors import _default_sync_schedule_for_scope


@pytest.mark.asyncio
async def test_start_google_auth_route_accepts_post_auth_provider_action(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_start_google_login(
        _session: object,
        *,
        return_path: str = "/",
        post_auth_action: str | None = None,
        owner_scope: str | None = None,
        provider: str | None = None,
    ) -> OAuthStartResponse:
        captured.update(
            {
                "return_path": return_path,
                "post_auth_action": post_auth_action,
                "owner_scope": owner_scope,
                "provider": provider,
            }
        )
        return OAuthStartResponse(authorization_url="https://accounts.example.test/auth", state="state-token")

    monkeypatch.setattr(auth_route, "start_google_login", fake_start_google_login)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/auth/google/start",
            params={
                "return_to": "/connectors",
                "post_auth_action": "connect_provider",
                "owner_scope": "workspace",
                "provider": "notion",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "return_path": "/connectors",
        "post_auth_action": "connect_provider",
        "owner_scope": "workspace",
        "provider": "notion",
    }
    assert response.json()["authorization_url"] == "https://accounts.example.test/auth"


@pytest.mark.asyncio
async def test_connectors_readiness_route_allows_anonymous_view(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def override_optional_auth():
        return None

    async def fake_get_connectors_readiness(_session: object, _auth_user: object | None) -> ConnectorReadinessResponse:
        return ConnectorReadinessResponse(
            providers=[
                {
                    "provider": "google_drive",
                    "oauth_configured": True,
                    "workspace_connection_exists": False,
                    "workspace_connection_status": None,
                    "viewer_can_manage_workspace_connection": False,
                    "setup_state": "setup_needed",
                    "healthy_source_count": 0,
                    "needs_attention_count": 0,
                    "recommended_templates": ["shared_drive", "folder"],
                },
                {
                    "provider": "notion",
                    "oauth_configured": False,
                    "workspace_connection_exists": False,
                    "workspace_connection_status": None,
                    "viewer_can_manage_workspace_connection": False,
                    "setup_state": "not_configured",
                    "healthy_source_count": 0,
                    "needs_attention_count": 0,
                    "recommended_templates": ["page", "database"],
                },
            ]
        )

    monkeypatch.setattr(connectors_route, "get_connectors_readiness", fake_get_connectors_readiness)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = override_optional_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/connectors/readiness")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "providers": [
            {
                "provider": "google_drive",
                "oauth_configured": True,
                "workspace_connection_exists": False,
                "workspace_connection_status": None,
                "viewer_can_manage_workspace_connection": False,
                "setup_state": "setup_needed",
                "healthy_source_count": 0,
                "needs_attention_count": 0,
                "recommended_templates": ["shared_drive", "folder"],
            },
            {
                "provider": "notion",
                "oauth_configured": False,
                "workspace_connection_exists": False,
                "workspace_connection_status": None,
                "viewer_can_manage_workspace_connection": False,
                "setup_state": "not_configured",
                "healthy_source_count": 0,
                "needs_attention_count": 0,
                "recommended_templates": ["page", "database"],
            },
        ]
    }


def test_default_sync_schedule_uses_scope_defaults() -> None:
    assert _default_sync_schedule_for_scope("workspace") == ("auto", 60)
    assert _default_sync_schedule_for_scope("personal") == ("manual", None)
