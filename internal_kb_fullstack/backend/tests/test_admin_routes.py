from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_admin_user
from app.db.engine import get_db_session
from app.db.models import ConnectorConnection, ConnectorResource, ConnectorSyncJob
from app.main import app
from app.services.auth import AuthenticatedUser
from app.services.auth import AuthForbiddenError


@pytest.mark.asyncio
async def test_jobs_route_requires_authentication() -> None:
    async def override_session():
        yield object()

    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/jobs")

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


@pytest.mark.asyncio
async def test_jobs_route_rejects_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_require_admin_user(_session, _session_token):
        raise AuthForbiddenError("Admin permission required.")

    monkeypatch.setattr("app.api.deps.require_admin_user", fake_require_admin_user)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/jobs", headers={"X-KB-Session": "member-session"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin permission required."


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class FakeScalarsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class JobsSession:
    def __init__(self, *, connection: ConnectorConnection, resource: ConnectorResource, job: ConnectorSyncJob) -> None:
        self.connection = connection
        self.resource = resource
        self.job = job

    async def execute(self, statement):
        descriptions = getattr(statement, "column_descriptions", None) or []
        if descriptions:
            entity = descriptions[0].get("entity")
            if entity is ConnectorSyncJob:
                return FakeScalarsResult([self.job])
            if entity is ConnectorResource:
                return FakeScalarsResult([self.resource])
        return FakeScalarsResult([])

    async def get(self, model, identifier):
        if model is ConnectorSyncJob and identifier == self.job.id:
            return self.job
        if model is ConnectorResource and identifier == self.resource.id:
            return self.resource
        if model is ConnectorConnection and identifier == self.connection.id:
            return self.connection
        return None


def make_admin_user(*, workspace_id) -> AuthenticatedUser:
    return AuthenticatedUser(
        user=SimpleNamespace(id=uuid4(), email="owner@example.com", name="Owner", avatar_url=None),
        roles=["member"],
        current_workspace_id=workspace_id,
        current_workspace_slug="default",
        current_workspace_name="Default Workspace",
        current_workspace_role="owner",
    )


@pytest.mark.asyncio
async def test_jobs_routes_list_and_detail_connector_jobs_for_current_workspace() -> None:
    workspace_id = uuid4()
    connection_id = uuid4()
    resource_id = uuid4()
    job_id = uuid4()
    now = datetime.now(timezone.utc)
    session = JobsSession(
        connection=ConnectorConnection(
            id=connection_id,
            provider="notion",
            workspace_id=workspace_id,
            owner_scope="workspace",
            owner_user_id=None,
            display_name="Workspace Notion",
            account_email=None,
            account_subject="notion-account",
            status="active",
            encrypted_access_token="token",
            encrypted_refresh_token=None,
            token_expires_at=None,
            granted_scopes=[],
            last_validated_at=now,
            created_at=now,
            updated_at=now,
        ),
        resource=ConnectorResource(
            id=resource_id,
            connection_id=connection_id,
            provider="notion",
            resource_kind="page",
            external_id="page-1",
            name="Operations Page",
            resource_url="https://www.notion.so/page-1",
            parent_external_id=None,
            sync_children=True,
            visibility_scope="member_visible",
            selection_mode="browse",
            sync_mode="manual",
            sync_interval_minutes=None,
            status="active",
            sync_cursor=None,
            last_sync_started_at=None,
            last_sync_completed_at=None,
            next_auto_sync_at=None,
            last_sync_summary={},
            provider_metadata={},
            created_at=now,
            updated_at=now,
        ),
        job=ConnectorSyncJob(
            id=job_id,
            kind="sync",
            connection_id=connection_id,
            resource_id=resource_id,
            sync_mode="manual",
            status="queued",
            priority=90,
            attempt_count=0,
            error_message=None,
            payload={},
            requested_at=now,
            started_at=None,
            last_heartbeat_at=None,
            finished_at=None,
        ),
    )

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_admin_user] = lambda: make_admin_user(workspace_id=workspace_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        list_response = await client.get("/v1/jobs")
        detail_response = await client.get(f"/v1/jobs/{job_id}")

    app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()[0]["connection_id"] == str(connection_id)
    assert list_response.json()[0]["resource_id"] == str(resource_id)
    assert list_response.json()[0]["title"] == "리소스 동기화: Operations Page"

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == str(job_id)
    assert detail_response.json()["connection_id"] == str(connection_id)
    assert detail_response.json()["resource_id"] == str(resource_id)
