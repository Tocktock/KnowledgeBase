from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_authenticated_user, get_optional_authenticated_user
from app.api.routes import auth as auth_route
from app.api.routes import connectors as connectors_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.auth import OAuthStartResponse
from app.schemas.connectors import ConnectorOAuthCallbackResponse, ConnectorReadinessResponse
from app.services.auth import AuthenticatedUser
from app.services.connectors import (
    ConnectorError,
    ConnectorForbiddenError,
    _default_sync_schedule_for_scope,
    _github_doc_path_supported,
    _resource_supports_connector_sync,
    _validate_resource_kind,
    request_resource_sync,
)
from app.services import connectors as connector_service


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
async def test_start_provider_oauth_route_maps_workspace_admin_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")

    async def override_session():
        yield object()

    async def fake_start_provider_oauth(*_args, **_kwargs):
        raise ConnectorForbiddenError("Workspace admin permission required.")

    monkeypatch.setattr(connectors_route, "start_provider_oauth", fake_start_provider_oauth)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/connectors/google-drive/oauth/start", params={"owner_scope": "workspace"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Workspace admin permission required."}


@pytest.mark.asyncio
async def test_complete_provider_oauth_route_maps_invalid_state_to_bad_request(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="owner")

    async def override_session():
        yield object()

    async def fake_complete_provider_oauth(*_args, **_kwargs) -> ConnectorOAuthCallbackResponse:
        raise ConnectorError("Connector OAuth state is invalid or expired.")

    monkeypatch.setattr(connectors_route, "complete_provider_oauth", fake_complete_provider_oauth)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/connectors/google-drive/oauth/callback",
            params={"state": "bad-state", "code": "code-123"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "Connector OAuth state is invalid or expired."}


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
                    "provider": "github",
                    "oauth_configured": True,
                    "workspace_connection_exists": False,
                    "workspace_connection_status": None,
                    "viewer_can_manage_workspace_connection": False,
                    "setup_state": "setup_needed",
                    "healthy_source_count": 0,
                    "needs_attention_count": 0,
                    "recommended_templates": ["repository_docs", "repository_evidence"],
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
                    "recommended_templates": ["page", "database", "export_upload"],
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
                "provider": "github",
                "oauth_configured": True,
                "workspace_connection_exists": False,
                "workspace_connection_status": None,
                "viewer_can_manage_workspace_connection": False,
                "setup_state": "setup_needed",
                "healthy_source_count": 0,
                "needs_attention_count": 0,
                "recommended_templates": ["repository_docs", "repository_evidence"],
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
                "recommended_templates": ["page", "database", "export_upload"],
            },
        ]
    }


def test_default_sync_schedule_uses_scope_defaults() -> None:
    assert _default_sync_schedule_for_scope("workspace") == ("auto", 60)
    assert _default_sync_schedule_for_scope("personal") == ("manual", None)


def test_validate_resource_kind_accepts_github_repository_docs() -> None:
    assert _validate_resource_kind("github", "repository_docs") == "repository_docs"
    assert _validate_resource_kind("github", "repository_evidence") == "repository_evidence"
    assert _validate_resource_kind("notion", "export_upload") == "export_upload"


def test_github_doc_path_supported_filters_expected_files() -> None:
    assert _github_doc_path_supported("README.md") is True
    assert _github_doc_path_supported("docs/architecture.md") is True
    assert _github_doc_path_supported("doc/runbook.txt") is True
    assert _github_doc_path_supported("src/index.ts") is False
    assert _github_doc_path_supported("docs/logo.png") is False


def test_resource_supports_connector_sync_rejects_uploaded_exports() -> None:
    assert _resource_supports_connector_sync(SimpleNamespace(selection_mode="browse")) is True
    assert _resource_supports_connector_sync(SimpleNamespace(selection_mode="search")) is True
    assert _resource_supports_connector_sync(SimpleNamespace(selection_mode="export_upload")) is False


@pytest.mark.asyncio
async def test_request_resource_sync_rejects_uploaded_export_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="owner")
    connection = SimpleNamespace(id=uuid4(), owner_scope="workspace")
    resource = SimpleNamespace(id=uuid4(), connection_id=connection.id, selection_mode="export_upload")
    enqueue_called = False

    async def fake_get_connection_or_raise(_session, _connection_id, _auth_user):
        return connection

    async def fake_get_resource_or_raise(_session, _resource_id):
        return resource

    async def fake_enqueue_connector_sync_job(*args, **kwargs):
        nonlocal enqueue_called
        enqueue_called = True
        raise AssertionError("enqueue_connector_sync_job should not be called for uploaded exports")

    monkeypatch.setattr(connector_service, "_get_connection_or_raise", fake_get_connection_or_raise)
    monkeypatch.setattr(connector_service, "_get_resource_or_raise", fake_get_resource_or_raise)
    monkeypatch.setattr(connector_service, "enqueue_connector_sync_job", fake_enqueue_connector_sync_job)

    with pytest.raises(connector_service.ConnectorError, match="업로드형 내보내기는 새 파일 업로드로 갱신하세요."):
        await request_resource_sync(object(), auth_user, connection.id, resource.id)

    assert enqueue_called is False
