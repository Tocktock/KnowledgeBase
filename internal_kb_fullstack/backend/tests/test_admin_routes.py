from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.engine import get_db_session
from app.main import app
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
