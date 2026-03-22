from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import Document, KnowledgeConcept
from app.schemas.glossary import GlossaryConceptUpdateRequest
from app.services import glossary as glossary_service
from app.services.glossary import GlossaryError, update_glossary_concept


class StubSession:
    def __init__(self, documents: dict[object, Document] | None = None) -> None:
        self.documents = documents or {}
        self.commit_calls = 0

    async def get(self, model: object, identifier: object):
        if model is Document:
            return self.documents.get(identifier)
        return None

    async def commit(self) -> None:
        self.commit_calls += 1

    async def execute(self, _stmt: object):
        class Result:
            def scalar_one_or_none(self) -> None:
                return None

        return Result()


@pytest.mark.asyncio
async def test_update_glossary_concept_approve_publishes_canonical_document(monkeypatch: pytest.MonkeyPatch) -> None:
    document = Document(
        id=uuid4(),
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

    async def fake_get_glossary_concept_detail(_session: object, _concept_id: object):
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
