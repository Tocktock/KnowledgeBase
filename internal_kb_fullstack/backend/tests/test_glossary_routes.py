from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import glossary as glossary_route
from app.api.routes import search as search_route
from app.db.engine import get_db_session
from app.main import app
from app.schemas.glossary import (
    GlossaryConceptDetailResponse,
    GlossaryConceptDocumentLink,
    GlossaryConceptSummary,
    GlossarySupportItem,
)
from app.schemas.search import SearchExplainResponse, SearchHit, SearchResponse
from app.schemas.trust import TrustSummary
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


@pytest.mark.asyncio
async def test_search_route_returns_concept_aware_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_search_documents(_session: object, _payload: object) -> SearchResponse:
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

    async def fake_explain_search(_session: object, _payload: object) -> SearchExplainResponse:
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

    async def override_session():
        yield session

    async def fake_enqueue_glossary_refresh_job(_session: object, *, scope: str = "full", target_document_id: object = None, priority: int = 200):
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
async def test_glossary_by_slug_route_maps_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_session():
        yield object()

    async def fake_get_glossary_concept_by_slug(_session: object, _slug: str):
        raise GlossaryNotFoundError("Glossary concept not found")

    monkeypatch.setattr(glossary_route, "get_glossary_concept_by_slug", fake_get_glossary_concept_by_slug)
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

    async def override_session():
        yield session

    async def fake_create_or_regenerate_glossary_draft(_session: object, _concept_id: object, _payload: object) -> GlossaryConceptDetailResponse:
        return detail

    monkeypatch.setattr(glossary_route, "create_or_regenerate_glossary_draft", fake_create_or_regenerate_glossary_draft)
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/v1/glossary/{detail.concept.id}/draft", json={"domain": "차량 분류"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["concept"]["display_term"] == "센디 차량"
    assert session.flush_calls == 1
    assert session.commit_calls == 1
