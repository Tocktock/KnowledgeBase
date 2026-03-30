from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import ConceptStatus, Document, KnowledgeConcept
from app.schemas.glossary import GlossaryConceptRequestCreateRequest, GlossaryConceptUpdateRequest
from app.services import glossary as glossary_service
from app.services.glossary import (
    GlossaryError,
    create_glossary_concept_request,
    create_or_regenerate_glossary_draft,
    list_glossary_concept_requests_for_user,
    update_glossary_concept,
)


class StubSession:
    def __init__(self, documents: dict[object, Document] | None = None, concepts: list[KnowledgeConcept] | None = None) -> None:
        self.documents = documents or {}
        self.concepts = concepts or []
        self.commit_calls = 0
        self.flush_calls = 0
        self.added: list[object] = []

    async def get(self, model: object, identifier: object):
        if model is Document:
            return self.documents.get(identifier)
        if model is KnowledgeConcept:
            return next((concept for concept in self.concepts if concept.id == identifier), None)
        return None

    async def commit(self) -> None:
        self.commit_calls += 1

    async def flush(self) -> None:
        self.flush_calls += 1

    def add(self, item: object) -> None:
        self.added.append(item)
        if isinstance(item, KnowledgeConcept):
            if item.id is None:
                item.id = uuid4()
            now = datetime.now(timezone.utc)
            if item.created_at is None:
                item.created_at = now
            if item.updated_at is None:
                item.updated_at = now
            if item.refreshed_at is None:
                item.refreshed_at = now
            self.concepts.append(item)

    async def execute(self, _stmt: object):
        concepts = list(self.concepts)

        class Result:
            def __init__(self, values: list[KnowledgeConcept]) -> None:
                self.values = values

            def scalar_one_or_none(self) -> None:
                return None

            def scalars(self):
                class Scalars:
                    def __init__(self, values: list[KnowledgeConcept]) -> None:
                        self.values = values

                    def all(self) -> list[KnowledgeConcept]:
                        return self.values

                return Scalars(self.values)

        return Result(concepts)


@pytest.mark.asyncio
async def test_update_glossary_concept_approve_publishes_canonical_document(monkeypatch: pytest.MonkeyPatch) -> None:
    document = Document(
        id=uuid4(),
        workspace_id=uuid4(),
        source_system="glossary",
        source_external_id="concept:draft",
        source_url="glossary://concept/test",
        slug="glossary-센디-차량",
        title="센디 차량",
        language_code="ko",
        doc_type="glossary",
        status="draft",
        owner_team=None,
        meta={},
        current_revision_id=None,
    )
    concept = KnowledgeConcept(
        id=uuid4(),
        workspace_id=document.workspace_id,
        normalized_term="센디 차량",
        display_term="센디 차량",
        aliases=["센디 차량"],
        language_code="ko",
        concept_type="product",
        confidence_score=0.99,
        support_doc_count=4,
        support_chunk_count=4,
        status="drafted",
        owner_team_hint="product",
        source_system_mix=["notion-export"],
        generated_document_id=document.id,
        canonical_document_id=None,
        meta={},
    )
    session = StubSession(documents={document.id: document})

    async def fake_get_concept_or_raise(_session: object, _concept_id: object) -> KnowledgeConcept:
        return concept

    async def fake_get_glossary_concept_detail(_session: object, _concept_id: object, *, workspace_id=None):
        assert workspace_id == concept.workspace_id
        return SimpleNamespace(concept=SimpleNamespace(status=concept.status, canonical_document_id=concept.canonical_document_id))

    monkeypatch.setattr(glossary_service, "_get_concept_or_raise", fake_get_concept_or_raise)
    monkeypatch.setattr(glossary_service, "get_glossary_concept_detail", fake_get_glossary_concept_detail)

    result = await update_glossary_concept(session, concept.id, GlossaryConceptUpdateRequest(action="approve"))

    assert document.status == "published"
    assert document.doc_type == "glossary"
    assert document.owner_team == "product"
    assert concept.status == "approved"
    assert concept.canonical_document_id == document.id
    assert concept.generated_document_id is None
    assert session.commit_calls == 1
    assert result.concept.status == "approved"


@pytest.mark.asyncio
async def test_update_glossary_concept_approve_requires_canonical_document(monkeypatch: pytest.MonkeyPatch) -> None:
    concept = KnowledgeConcept(
        id=uuid4(),
        workspace_id=uuid4(),
        normalized_term="디비딥",
        display_term="디비딥",
        aliases=["디비딥"],
        language_code="ko",
        concept_type="term",
        confidence_score=0.99,
        support_doc_count=3,
        support_chunk_count=4,
        status="suggested",
        owner_team_hint="product",
        source_system_mix=["notion-export"],
        generated_document_id=None,
        canonical_document_id=None,
        meta={},
    )
    session = StubSession()

    async def fake_get_concept_or_raise(_session: object, _concept_id: object) -> KnowledgeConcept:
        return concept

    monkeypatch.setattr(glossary_service, "_get_concept_or_raise", fake_get_concept_or_raise)

    with pytest.raises(GlossaryError, match="canonical glossary document is required"):
        await update_glossary_concept(session, concept.id, GlossaryConceptUpdateRequest(action="approve"))


@pytest.mark.asyncio
async def test_create_glossary_concept_request_creates_suggested_manual_request(monkeypatch: pytest.MonkeyPatch) -> None:
    session = StubSession()
    created_detail = None

    async def fake_get_glossary_concept_detail(_session: object, concept_id: object):
        nonlocal created_detail
        created = next(concept for concept in session.concepts if concept.id == concept_id)
        created_detail = created
        return SimpleNamespace(concept=glossary_service._concept_summary(created, {}))

    monkeypatch.setattr(glossary_service, "get_glossary_concept_detail", fake_get_glossary_concept_detail)

    response = await create_glossary_concept_request(
        session,
        workspace_id=uuid4(),
        requested_by_user_id=uuid4(),
        requested_by_name="Requester",
        requested_by_email="requester@example.com",
        payload=GlossaryConceptRequestCreateRequest(
            term="신규 용어",
            aliases=["신규 개념"],
            request_note="운영 정책 문서에서 계속 쓰입니다.",
            owner_team_hint="operations",
        ),
    )

    assert response.request_status == "created"
    assert created_detail is not None
    assert created_detail.status == ConceptStatus.suggested.value
    assert created_detail.meta["request_source"] == "manual_request"
    assert created_detail.meta["manual_request_count"] == 1
    assert session.commit_calls == 1
    assert session.flush_calls == 2


@pytest.mark.asyncio
async def test_create_glossary_draft_uses_manual_request_fallback_when_no_support(monkeypatch: pytest.MonkeyPatch) -> None:
    concept = KnowledgeConcept(
        id=uuid4(),
        workspace_id=uuid4(),
        normalized_term="신규 용어",
        display_term="신규 용어",
        aliases=["신규 용어", "신규 개념"],
        language_code="ko",
        concept_type="term",
        confidence_score=0.0,
        support_doc_count=0,
        support_chunk_count=0,
        status=ConceptStatus.suggested.value,
        owner_team_hint="operations",
        source_system_mix=[],
        meta={
            "manual_request_count": 1,
            "manual_request_latest": {
                "requested_by_name": "Requester",
                "requested_by_email": "requester@example.com",
                "request_note": "운영 정책 문서에서 계속 쓰입니다.",
                "requested_at": "2026-03-29T00:00:00+00:00",
            },
            "manual_requests": [
                {
                    "requested_by_name": "Requester",
                    "requested_by_email": "requester@example.com",
                    "request_note": "운영 정책 문서에서 계속 쓰입니다.",
                    "requested_at": "2026-03-29T00:00:00+00:00",
                }
            ],
        },
    )
    session = StubSession(concepts=[concept])
    ingested_markdown: str | None = None
    generated_document_id = uuid4()

    async def fake_get_concept_or_raise(_session: object, _concept_id: object) -> KnowledgeConcept:
        return concept

    async def fake_get_concept_support_hits(_session: object, _concept_id: object, *, workspace_id=None, limit: int):
        assert workspace_id == concept.workspace_id
        assert limit == 8
        return []

    async def fake_ingest_document(_session: object, payload: object, *, workspace_id):
        assert workspace_id == concept.workspace_id
        nonlocal ingested_markdown
        ingested_markdown = payload.content
        return SimpleNamespace(document=SimpleNamespace(id=generated_document_id))

    async def fake_get_glossary_concept_detail(_session: object, _concept_id: object, *, workspace_id=None):
        assert workspace_id == concept.workspace_id
        return SimpleNamespace(
            concept=SimpleNamespace(
                id=concept.id,
                status=concept.status,
                generated_document_id=concept.generated_document_id,
                validation_reason=concept.validation_reason,
            )
        )

    monkeypatch.setattr(glossary_service, "_get_concept_or_raise", fake_get_concept_or_raise)
    monkeypatch.setattr(glossary_service, "get_concept_support_hits", fake_get_concept_support_hits)
    monkeypatch.setattr(glossary_service, "get_glossary_concept_detail", fake_get_glossary_concept_detail)
    monkeypatch.setattr("app.services.ingest.ingest_document", fake_ingest_document)

    result = await create_or_regenerate_glossary_draft(
        session,
        concept.id,
        glossary_service.GlossaryDraftRequest(domain="운영", regenerate=True),
    )

    assert ingested_markdown is not None
    assert "운영 정책 문서에서 계속 쓰입니다." in ingested_markdown
    assert "This draft was created from a manual glossary request" in ingested_markdown
    assert concept.generated_document_id == generated_document_id
    assert concept.status == ConceptStatus.drafted.value
    assert "작업 초안" in (concept.validation_reason or "")
    assert session.commit_calls == 1
    assert result.concept.status == ConceptStatus.drafted.value


@pytest.mark.asyncio
async def test_list_glossary_concept_requests_for_user_filters_to_current_user_and_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    other_workspace_id = uuid4()
    other_user_id = uuid4()
    now = datetime.now(timezone.utc)
    matching_concept = KnowledgeConcept(
        id=uuid4(),
        workspace_id=workspace_id,
        normalized_term="신규 용어",
        display_term="신규 용어",
        aliases=["신규 용어"],
        language_code="ko",
        concept_type="term",
        confidence_score=0.2,
        support_doc_count=0,
        support_chunk_count=0,
        status=ConceptStatus.suggested.value,
        validation_state="new_term",
        owner_team_hint="operations",
        source_system_mix=[],
        meta={
            "manual_requests": [
                {
                    "workspace_id": str(workspace_id),
                    "requested_by_user_id": str(user_id),
                    "requested_by_name": "Requester",
                    "requested_by_email": "requester@example.com",
                    "request_note": "운영에서 쓰는 용어입니다.",
                    "requested_at": "2026-03-29T00:00:00+00:00",
                },
                {
                    "workspace_id": str(workspace_id),
                    "requested_by_user_id": str(user_id),
                    "requested_by_name": "Requester",
                    "requested_by_email": "requester@example.com",
                    "request_note": "추가 문맥입니다.",
                    "requested_at": "2026-03-29T01:00:00+00:00",
                },
            ]
        },
        refreshed_at=now,
        updated_at=now,
    )
    other_concept = KnowledgeConcept(
        id=uuid4(),
        workspace_id=other_workspace_id,
        normalized_term="다른 용어",
        display_term="다른 용어",
        aliases=["다른 용어"],
        language_code="ko",
        concept_type="term",
        confidence_score=0.2,
        support_doc_count=0,
        support_chunk_count=0,
        status=ConceptStatus.suggested.value,
        validation_state="new_term",
        owner_team_hint="product",
        source_system_mix=[],
        meta={
            "manual_requests": [
                {
                    "workspace_id": str(other_workspace_id),
                    "requested_by_user_id": str(other_user_id),
                    "requested_by_name": "Other",
                    "requested_by_email": "other@example.com",
                    "request_note": "다른 요청입니다.",
                    "requested_at": "2026-03-29T02:00:00+00:00",
                }
            ]
        },
        refreshed_at=now,
        updated_at=now,
    )
    session = StubSession(concepts=[matching_concept, other_concept])

    async def fake_load_linked_documents(_session: object, _doc_ids: set[object]):
        return {}

    monkeypatch.setattr(glossary_service, "_load_linked_documents", fake_load_linked_documents)

    response = await list_glossary_concept_requests_for_user(
        session,
        workspace_id=workspace_id,
        requested_by_user_id=user_id,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.items[0].concept.display_term == "신규 용어"
    assert response.items[0].request_count == 2
    assert response.items[0].latest_request.request_note == "추가 문맥입니다."
