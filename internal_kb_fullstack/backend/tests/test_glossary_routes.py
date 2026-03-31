from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_authenticated_user, get_optional_authenticated_user
from app.api.routes import glossary as glossary_route
from app.api.routes import search as search_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.glossary import (
    GlossaryConceptDetailResponse,
    GlossaryConceptDocumentLink,
    GlossaryConceptRequestListEntry,
    GlossaryConceptRequestListItem,
    GlossaryConceptRequestListResponse,
    GlossaryConceptRequestResponse,
    GlossaryConceptSummary,
    GlossarySupportItem,
    GlossaryValidationRunSummary,
)
from app.schemas.search import SearchExplainResponse, SearchHit, SearchResponse
from app.schemas.trust import TrustSummary, VerificationSummary
from app.services.auth import AuthenticatedUser
from app.services.glossary import GlossaryNotFoundError


class StubSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.refresh_calls = 0

    def add(self, item: object) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        self.flush_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, _item: object) -> None:
        self.refresh_calls += 1


def make_glossary_summary() -> GlossaryConceptSummary:
    concept_id = uuid4()
    generated_doc = GlossaryConceptDocumentLink(
        id=uuid4(),
        slug="glossary-센디-차량",
        title="센디 차량",
        status="draft",
        doc_type="glossary",
        owner_team="product",
    )
    return GlossaryConceptSummary(
        id=concept_id,
        slug="센디-차량",
        normalized_term="센디 차량",
        display_term="센디 차량",
        aliases=["센디 차량", "센디 차량 (1)"],
        language_code="ko",
        concept_type="product",
        confidence_score=0.91,
        support_doc_count=4,
        support_chunk_count=9,
        status="drafted",
        validation_state="missing_draft",
        validation_reason="센디 차량은 근거는 충분하지만 작업 초안이 아직 없습니다.",
        last_validated_at=datetime.now(timezone.utc),
        review_required=True,
        last_validation_run_id=uuid4(),
        verification_state="monitoring",
        verification=VerificationSummary(
            status="monitoring",
            policy_label="Default glossary verification",
            policy_version=1,
            evidence_bundle_hash="bundle-hash",
            verified_at=None,
            due_at=datetime.now(timezone.utc),
            last_checked_at=datetime.now(timezone.utc),
            verified_by=None,
            reason="센디 차량 satisfies the current evidence policy but is still awaiting or retaining review attention.",
        ),
        owner_team_hint="product",
        source_system_mix=["notion-export"],
        generated_document=generated_doc,
        canonical_document=None,
        metadata={},
        refreshed_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        trust=TrustSummary(
            source_label="Notion",
            source_url="glossary://concept/1",
            authority_kind="approved_concept",
            last_synced_at=datetime.now(timezone.utc),
            freshness_state="fresh",
            evidence_count=4,
        ),
    )


def make_glossary_detail() -> GlossaryConceptDetailResponse:
    summary = make_glossary_summary()
    return GlossaryConceptDetailResponse(
        concept=summary,
        supports=[
            GlossarySupportItem(
                id=uuid4(),
                document_id=uuid4(),
                document_slug="센디-차량-d1eb3f3193",
                document_title="센디 차량",
                document_status="published",
                document_doc_type="knowledge",
                owner_team="product",
                revision_id=uuid4(),
                chunk_id=uuid4(),
                evidence_kind="title",
                evidence_term="센디 차량",
                evidence_strength=3.6,
                support_group_key="센디 차량",
                support_text="센디 차량은 차량 분류 기준 문서입니다.",
                metadata={},
                trust=TrustSummary(
                    source_label="Notion",
                    source_url="glossary://concept/1",
                    authority_kind="concept_evidence",
                    last_synced_at=datetime.now(timezone.utc),
                    freshness_state="fresh",
                    evidence_count=4,
                ),
            )
        ],
        related_concepts=[],
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


async def fake_resolve_read_workspace_id(*_args, **_kwargs):
    return None


@pytest.mark.asyncio
async def test_search_route_returns_concept_aware_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_search_documents(_session: object, _payload: object, *, workspace_id=None) -> SearchResponse:
        assert workspace_id is None
        return SearchResponse(
            query="센디 차량",
            resolved_concept_id=uuid4(),
            resolved_concept_term="센디 차량",
            weak_grounding=False,
            notes=["Concept resolved from glossary support."],
            hits=[
                SearchHit(
                    chunk_id=uuid4(),
                    document_id=uuid4(),
                    revision_id=uuid4(),
                    document_title="센디 차량",
                    document_slug="glossary-센디-차량",
                    source_system="glossary",
                    source_url="glossary://concept/1",
                    section_title="Definition",
                    heading_path=["센디 차량"],
                    content_text="센디 차량은 차량 분류 기준 문서입니다.",
                    hybrid_score=100.0,
                    result_type="glossary",
                    matched_concept_term="센디 차량",
                    evidence_kind="canonical",
                    evidence_strength=1.9,
                    metadata={},
                    trust=TrustSummary(
                        source_label="Notion",
                        source_url="glossary://concept/1",
                        authority_kind="approved_concept",
                        last_synced_at=datetime.now(timezone.utc),
                        freshness_state="fresh",
                        evidence_count=1,
                    ),
                )
            ],
        )

    monkeypatch.setattr(search_route, "search_documents", fake_search_documents)
    monkeypatch.setattr(search_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/search", json={"query": "센디 차량"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_concept_term"] == "센디 차량"
    assert payload["hits"][0]["result_type"] == "glossary"
    assert payload["hits"][0]["evidence_kind"] == "canonical"


@pytest.mark.asyncio
async def test_search_explain_route_returns_debug_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_explain_search(_session: object, _payload: object, *, workspace_id=None) -> SearchExplainResponse:
        assert workspace_id is None
        return SearchExplainResponse(
            query="센디 차량",
            normalized_query="센디 차량",
            resolved_concept_id=uuid4(),
            resolved_concept_term="센디 차량",
            resolved_concept_status="approved",
            canonical_document_slug="glossary-센디-차량",
            weak_grounding=False,
            notes=["Canonical glossary document was selected first."],
            hits=[],
        )

    monkeypatch.setattr(search_route, "explain_search", fake_explain_search)
    monkeypatch.setattr(search_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/search/explain", json={"query": "센디 차량"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["canonical_document_slug"] == "glossary-센디-차량"


@pytest.mark.asyncio
async def test_glossary_refresh_route_returns_queued_job(monkeypatch: pytest.MonkeyPatch) -> None:
    session = StubSession()
    auth_user = make_auth_user(role="owner")

    async def override_session():
        yield session

    async def fake_enqueue_glossary_refresh_job(
        _session: object,
        *,
        workspace_id=None,
        scope: str = "full",
        target_document_id: object = None,
        priority: int = 200,
    ):
        assert workspace_id == auth_user.current_workspace_id
        return SimpleNamespace(
            id=uuid4(),
            kind="refresh",
            scope=scope,
            status="queued",
            target_concept_id=None,
            target_document_id=None,
            priority=priority,
            attempt_count=0,
            error_message=None,
            payload={"scope": scope},
            requested_at=datetime.now(timezone.utc),
            started_at=None,
            finished_at=None,
        )

    monkeypatch.setattr(glossary_route, "enqueue_glossary_refresh_job", fake_enqueue_glossary_refresh_job)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/glossary/refresh", json={"scope": "incremental"})

    app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["kind"] == "refresh"
    assert payload["title"] == "Glossary refresh (incremental)"
    assert session.commit_calls == 1
    assert session.refresh_calls == 1


@pytest.mark.asyncio
async def test_create_validation_run_route_returns_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="admin")

    async def override_session():
        yield object()

    async def fake_create_glossary_validation_run(_session: object, *, workspace_id, requested_by_user_id, payload):
        assert workspace_id == auth_user.current_workspace_id
        assert requested_by_user_id == auth_user.user.id
        assert payload.mode == "sync_validate_impacted"
        return GlossaryValidationRunSummary(
            id=uuid4(),
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            mode="sync_validate_impacted",
            status="queued",
            target_concept_id=None,
            source_scope="workspace_active",
            selected_resource_ids=[],
            source_sync_summary={"queued": 3},
            validation_summary={"updated_concepts": 0},
            linked_job_ids=[str(uuid4())],
            error_message=None,
            requested_at=datetime.now(timezone.utc),
            started_at=None,
            finished_at=None,
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(glossary_route, "create_glossary_validation_run", fake_create_glossary_validation_run)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/glossary/validation-runs", json={"mode": "sync_validate_impacted"})

    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["mode"] == "sync_validate_impacted"
    assert response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_glossary_request_route_returns_created_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")
    summary = make_glossary_summary()

    async def override_session():
        yield object()

    async def fake_create_glossary_concept_request(
        _session: object,
        *,
        workspace_id,
        requested_by_user_id,
        requested_by_name,
        requested_by_email,
        payload,
    ) -> GlossaryConceptRequestResponse:
        assert workspace_id == auth_user.current_workspace_id
        assert requested_by_user_id == auth_user.user.id
        assert requested_by_name == auth_user.user.name
        assert requested_by_email == auth_user.user.email
        assert payload.term == "신규 용어"
        return GlossaryConceptRequestResponse(
            request_status="created",
            message="새 핵심 개념 요청을 등록했습니다.",
            concept=summary,
        )

    monkeypatch.setattr(glossary_route, "create_glossary_concept_request", fake_create_glossary_concept_request)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/glossary/requests",
            json={"term": "신규 용어", "aliases": ["신규 개념"], "request_note": "운영에서 계속 씁니다."},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_status"] == "created"
    assert payload["concept"]["display_term"] == "센디 차량"


@pytest.mark.asyncio
async def test_glossary_request_route_requires_workspace_membership() -> None:
    auth_user = AuthenticatedUser(
        user=SimpleNamespace(id=uuid4(), email="member@example.com", name="Member", avatar_url=None),
        roles=["member"],
        current_workspace_id=None,
        current_workspace_slug=None,
        current_workspace_name=None,
        current_workspace_role=None,
    )

    async def override_session():
        yield object()

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/glossary/requests", json={"term": "신규 용어"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Glossary requests require an active workspace membership."


@pytest.mark.asyncio
async def test_glossary_request_list_route_returns_current_user_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    auth_user = make_auth_user(role="member")
    summary = make_glossary_summary()

    async def override_session():
        yield object()

    async def fake_list_glossary_concept_requests_for_user(_session: object, *, workspace_id, requested_by_user_id, limit: int, offset: int):
        assert workspace_id == auth_user.current_workspace_id
        assert requested_by_user_id == auth_user.user.id
        assert limit == 20
        assert offset == 0
        return GlossaryConceptRequestListResponse(
            items=[
                GlossaryConceptRequestListItem(
                    concept=summary,
                    latest_request=GlossaryConceptRequestListEntry(
                        requested_by_name=auth_user.user.name,
                        requested_by_email=auth_user.user.email,
                        request_note="운영에서 계속 쓰입니다.",
                        requested_at=datetime.now(timezone.utc),
                        owner_team_hint="operations",
                    ),
                    request_count=2,
                )
            ],
            total=1,
            limit=20,
            offset=0,
        )

    monkeypatch.setattr(glossary_route, "list_glossary_concept_requests_for_user", fake_list_glossary_concept_requests_for_user)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/glossary/requests")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["request_count"] == 2
    assert payload["items"][0]["concept"]["display_term"] == "센디 차량"
    assert payload["items"][0]["latest_request"]["request_note"] == "운영에서 계속 쓰입니다."


@pytest.mark.asyncio
async def test_glossary_by_slug_route_maps_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_get_glossary_concept_by_slug(
        _session: object,
        _slug: str,
        *,
        workspace_id=None,
        include_evidence_only_support: bool = False,
    ):
        assert workspace_id is None
        assert include_evidence_only_support is False
        raise GlossaryNotFoundError("Glossary concept not found")

    monkeypatch.setattr(glossary_route, "get_glossary_concept_by_slug", fake_get_glossary_concept_by_slug)
    monkeypatch.setattr(glossary_route, "resolve_read_workspace_id", fake_resolve_read_workspace_id)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/glossary/slug/missing")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Glossary concept not found"


@pytest.mark.asyncio
async def test_glossary_draft_route_returns_generated_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    session = StubSession()
    detail = make_glossary_detail()
    auth_user = make_auth_user(role="owner")

    async def override_session():
        yield session

    async def fake_create_or_regenerate_glossary_draft(
        _session: object,
        _concept_id: object,
        _payload: object,
        *,
        include_evidence_only_support: bool = False,
    ) -> GlossaryConceptDetailResponse:
        assert include_evidence_only_support is True
        return detail

    monkeypatch.setattr(glossary_route, "create_or_regenerate_glossary_draft", fake_create_or_regenerate_glossary_draft)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/v1/glossary/{detail.concept.id}/draft", json={"domain": "차량 분류"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["concept"]["display_term"] == "센디 차량"
    assert session.flush_calls == 1
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_glossary_by_slug_route_hides_evidence_support_for_member(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    auth_user = make_auth_user(role="member")
    auth_user.current_workspace_id = workspace_id
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_resolve_workspace(*_args, **_kwargs):
        return workspace_id

    async def fake_get_glossary_concept_by_slug(
        _session: object,
        _slug: str,
        *,
        workspace_id=None,
        include_evidence_only_support: bool = False,
    ):
        captured.update(
            {
                "workspace_id": workspace_id,
                "include_evidence_only_support": include_evidence_only_support,
            }
        )
        return make_glossary_detail()

    monkeypatch.setattr(glossary_route, "resolve_read_workspace_id", fake_resolve_workspace)
    monkeypatch.setattr(glossary_route, "get_glossary_concept_by_slug", fake_get_glossary_concept_by_slug)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/glossary/slug/센디-차량")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["include_evidence_only_support"] is False


@pytest.mark.asyncio
async def test_glossary_concept_route_includes_evidence_support_for_workspace_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    auth_user = make_auth_user(role="owner")
    auth_user.current_workspace_id = workspace_id
    detail = make_glossary_detail()
    captured: dict[str, object] = {}

    async def override_session():
        yield object()

    async def fake_resolve_workspace(*_args, **_kwargs):
        return workspace_id

    async def fake_get_glossary_concept_detail(
        _session: object,
        concept_id,
        *,
        workspace_id=None,
        include_evidence_only_support: bool = False,
    ):
        captured.update(
            {
                "concept_id": concept_id,
                "workspace_id": workspace_id,
                "include_evidence_only_support": include_evidence_only_support,
            }
        )
        return detail

    monkeypatch.setattr(glossary_route, "resolve_read_workspace_id", fake_resolve_workspace)
    monkeypatch.setattr(glossary_route, "get_glossary_concept_detail", fake_get_glossary_concept_detail)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_optional_authenticated_user] = lambda: auth_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/glossary/{detail.concept.id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["include_evidence_only_support"] is True
