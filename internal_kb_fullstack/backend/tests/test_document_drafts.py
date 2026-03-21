from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.documents import GenerateDefinitionDraftRequest
from app.schemas.search import SearchHit, SearchResponse
from app.services import document_drafts
from app.services.document_drafts import (
    DefinitionDraftNotFoundError,
    build_definition_query,
    select_reference_hits,
)


def make_hit(*, title: str, slug: str, content_text: str, section_title: str | None = None) -> SearchHit:
    return SearchHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        revision_id=uuid4(),
        document_title=title,
        document_slug=slug,
        source_system="notion-export",
        source_url=f"https://example.com/{slug}",
        section_title=section_title,
        heading_path=[title],
        content_text=content_text,
        hybrid_score=0.9,
        vector_score=0.8,
        keyword_score=0.7,
        metadata={},
    )


def test_build_definition_query_includes_domain_context() -> None:
    assert build_definition_query("Transport", "Carrier pricing") == "Transport Carrier pricing"
    assert build_definition_query("Transport", None) == "Transport"


def test_select_reference_hits_dedupes_repeated_chunks() -> None:
    first = make_hit(title="Transport Overview", slug="transport-overview", content_text="Transport connects shippers and carriers.")
    duplicate = first.model_copy()
    second = make_hit(title="Delivery SLA", slug="delivery-sla", content_text="Transport ownership includes handoff timing.")

    references = select_reference_hits([first, duplicate, second], limit=4)

    assert [reference.index for reference in references] == [1, 2]
    assert [reference.document_slug for reference in references] == ["transport-overview", "delivery-sla"]


@pytest.mark.asyncio
async def test_generate_definition_draft_returns_editable_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = [
        make_hit(
            title="Transport Overview",
            slug="transport-overview",
            section_title="Definition",
            content_text="Transport is the operating concept that coordinates shipment movement and handoff between teams.",
        ),
        make_hit(
            title="Carrier Playbook",
            slug="carrier-playbook",
            section_title="Operations",
            content_text="Transport work in this domain covers dispatch, tracking, and exception handling.",
        ),
    ]

    async def fake_hybrid_search(_session: object, payload: object) -> SearchResponse:
        assert getattr(payload, "query") == "Transport Delivery operations"
        return SearchResponse(query="Transport Delivery operations", hits=hits)

    class FakeGenerator:
        async def generate_body(self, *, topic: str, domain: str | None, references: list[object]) -> str:
            assert topic == "Transport"
            assert domain == "Delivery operations"
            assert len(references) == 2
            return (
                "## Definition\n"
                "Transport is the shared operating definition for moving shipments through the delivery lifecycle. [1]\n\n"
                "## How This Term Is Used Here\n"
                "The current corpus uses Transport for dispatch, tracking, and exception handling. [1][2]\n\n"
                "## Supporting Details\n"
                "- Teams coordinate shipment handoff and operational ownership. [2]\n\n"
                "## Open Questions\n"
                "- Which sub-domains should be excluded from this definition? [2]"
            )

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )
    monkeypatch.setattr(document_drafts, "get_definition_draft_generator", lambda: FakeGenerator())

    result = await document_drafts.generate_definition_draft(
        object(),
        GenerateDefinitionDraftRequest(topic="Transport", domain="Delivery operations"),
    )

    assert result.title == "Transport"
    assert result.slug == "transport"
    assert result.query == "Transport Delivery operations"
    assert result.markdown.startswith("# Transport")
    assert "## References" in result.markdown
    assert "[Transport Overview](/docs/transport-overview)" in result.markdown
    assert len(result.references) == 2


@pytest.mark.asyncio
async def test_generate_definition_draft_raises_when_no_references(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="Transport", hits=[])

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )

    with pytest.raises(DefinitionDraftNotFoundError):
        await document_drafts.generate_definition_draft(object(), GenerateDefinitionDraftRequest(topic="Transport"))
