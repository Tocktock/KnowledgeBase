from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.schemas.documents import GenerateDefinitionDraftRequest
from app.schemas.search import SearchHit, SearchResponse
from app.services import document_drafts
from app.services.document_drafts import (
    DefinitionDraftGenerationError,
    DefinitionDraftNotFoundError,
    DefinitionDraftValidationError,
    ReferenceCandidate,
    build_fallback_body,
    build_definition_query,
    filter_relevant_search_hits,
    _references_have_sufficient_grounding,
    repair_generated_body,
    select_reference_hits,
    validate_generated_body,
)


def make_hit(
    *,
    title: str,
    slug: str,
    content_text: str,
    section_title: str | None = None,
    document_id: UUID | None = None,
) -> SearchHit:
    return SearchHit(
        chunk_id=uuid4(),
        document_id=document_id or uuid4(),
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


def valid_body(*, details_citation: str = "[2]", open_questions: str = "- Which edge cases need a narrower scope?") -> str:
    return (
        "## Definition\n"
        "Transport is the shared operating definition for moving shipments through the delivery lifecycle. [1]\n\n"
        "## How This Term Is Used Here\n"
        "The current corpus uses Transport for dispatch, tracking, and exception handling. [1][2]\n\n"
        "## Supporting Details\n"
        f"- Teams coordinate shipment handoff and operational ownership. {details_citation}\n\n"
        "## Open Questions\n"
        f"{open_questions}"
    )


def test_build_definition_query_includes_domain_context() -> None:
    assert build_definition_query("Transport", "Carrier pricing") == "Transport Carrier pricing"
    assert build_definition_query("센디 차량", "차량 분류") == "센디 차량 분류"
    assert build_definition_query("Transport", None) == "Transport"


def test_select_reference_hits_dedupes_repeated_chunks() -> None:
    first = make_hit(title="Transport Overview", slug="transport-overview", content_text="Transport connects shippers and carriers.")
    duplicate = first.model_copy()
    second = make_hit(title="Delivery SLA", slug="delivery-sla", content_text="Transport ownership includes handoff timing.")

    references = select_reference_hits([first, duplicate, second], limit=4)

    assert [reference.index for reference in references] == [1, 2]
    assert [reference.document_slug for reference in references] == ["transport-overview", "delivery-sla"]


def test_select_reference_hits_prefers_unique_documents_before_extra_chunks() -> None:
    shared_document_id = uuid4()
    primary_first = make_hit(
        title="Transport Overview",
        slug="transport-overview",
        section_title="Definition",
        content_text="Primary reference.",
        document_id=shared_document_id,
    )
    primary_second = make_hit(
        title="Transport Overview",
        slug="transport-overview",
        section_title="Details",
        content_text="Secondary reference.",
        document_id=shared_document_id,
    )
    other = make_hit(title="Carrier Playbook", slug="carrier-playbook", section_title="Operations", content_text="Other document.")

    references = select_reference_hits([primary_first, primary_second, other], limit=2)

    assert [reference.document_slug for reference in references] == ["transport-overview", "carrier-playbook"]


def test_filter_relevant_search_hits_removes_irrelevant_neighbors() -> None:
    relevant = make_hit(
        title="센디 차량",
        slug="센디-차량-d1eb3f3193",
        section_title="센디 차량",
        content_text="센디 차량은 차량 분류와 옵션 정보를 정리한 문서입니다.",
    )
    irrelevant = make_hit(
        title="Codex Slug Review Conflict",
        slug="codexslugreviewdoc",
        section_title="Codex Slug Review Conflict",
        content_text="Second body for conflict handling.",
    )

    filtered = filter_relevant_search_hits([relevant, irrelevant], topic="센디 차량", domain="차량 분류")

    assert [hit.document_slug for hit in filtered] == ["센디-차량-d1eb3f3193"]


def test_validate_generated_body_accepts_valid_citations() -> None:
    validate_generated_body(valid_body(), reference_count=2)


def test_validate_generated_body_rejects_out_of_range_citations() -> None:
    with pytest.raises(DefinitionDraftValidationError, match="do not exist: 9"):
        validate_generated_body(valid_body(details_citation="[9]"), reference_count=2)


def test_validate_generated_body_requires_citations_in_required_sections() -> None:
    body = (
        "## Definition\n"
        "Transport is the shared operating definition for moving shipments through the delivery lifecycle.\n\n"
        "## How This Term Is Used Here\n"
        "The current corpus uses Transport for dispatch and tracking. [1]\n\n"
        "## Supporting Details\n"
        "- Teams coordinate shipment handoff and operational ownership. [2]\n\n"
        "## Open Questions\n"
        "- Which edge cases need a narrower scope?"
    )

    with pytest.raises(DefinitionDraftValidationError, match="Definition"):
        validate_generated_body(body, reference_count=2)


def test_validate_generated_body_allows_uncited_open_questions() -> None:
    validate_generated_body(valid_body(open_questions="- Which teams should own escalation rules?"), reference_count=2)


def test_repair_generated_body_adds_missing_citations_from_reference_overlap() -> None:
    references = select_reference_hits(
        [
            make_hit(title="센디 차량", slug="센디-차량-d1eb3f3193", content_text="센디 차량은 차량 종류와 옵션 정보를 정리한 문서입니다."),
            make_hit(title="다마스, 라보", slug="다마스-라보-926d876185", content_text="차량 종류와 옵션별 제약을 정리합니다."),
        ],
        limit=2,
    )
    body = (
        "## Definition\n"
        "센디 차량은 차량 종류와 옵션을 정리한 기준 문서입니다. [1]\n\n"
        "## How This Term Is Used Here\n"
        "운송 화면에서는 차량 종류와 옵션 선택에 이 용어를 사용합니다.\n\n"
        "## Supporting Details\n"
        "- 차종별 제약과 옵션 조합을 함께 확인합니다.\n\n"
        "## Open Questions\n"
        "- 어떤 차종 설명을 더 추가할까요?"
    )

    repaired = repair_generated_body(body, references)

    assert repaired is not None
    validate_generated_body(repaired, reference_count=2)
    assert "운송 화면에서는 차량 종류와 옵션 선택에 이 용어를 사용합니다. [1]" in repaired


def test_build_fallback_body_prefers_korean_copy_for_korean_topics() -> None:
    references = select_reference_hits(
        [
            make_hit(title="센디 차량", slug="센디-차량-d1eb3f3193", content_text="센디 차량은 차량 종류와 옵션 정보를 정리한 문서입니다."),
            make_hit(title="다마스, 라보", slug="다마스-라보-926d876185", content_text="차량 종류와 옵션별 제약을 정리합니다."),
        ],
        limit=2,
    )

    body = build_fallback_body(topic="센디 차량", domain="차량 분류", references=references)

    assert "센디 차량은 현재 코퍼스의 근거 문서를 바탕으로 정리한 개념 초안입니다. [1]" in body
    assert "현재 지식베이스에서는 센디 차량 및 다마스, 라보 같은 문서에서 이 용어를 사용합니다. [1][2]" in body
    assert "센디 차량과 관련된 도메인별 예외 케이스" in body


def test_validate_generated_body_accepts_unknown_middle_heading_after_normalization() -> None:
    body = (
        "## Definition\n"
        "센디 차량은 차량 분류 기준입니다. [1]\n\n"
        "## How This Term Is Used Here\n"
        "현재 센디 차량 관련 문서에서 이 용어를 사용합니다. [1]\n\n"
        "## Supporting Details\n"
        "- 차량 옵션과 차종 제약을 함께 확인합니다. [1]\n\n"
        "## Caveats\n"
        "문서별 표현 차이가 있어 편집 검토가 필요합니다. [1]\n\n"
        "## Open Questions\n"
        "- 어떤 차량 설명을 더 보강해야 할까요?"
    )

    validate_generated_body(body, reference_count=1)


def test_references_have_sufficient_grounding_requires_multiple_strong_documents() -> None:
    single = select_reference_hits(
        [make_hit(title="내부배차율 하락 원인 파악", slug="내부배차율-하락-원인-파악", content_text="단일 문서입니다.")],
        limit=1,
    )
    strong_candidate = ReferenceCandidate(
        reference=single[0],
        stage_rank=0,
        score=4.0,
        family_key="내부배차율 하락 원인 파악",
        order_index=0,
    )

    assert not _references_have_sufficient_grounding(single, {str(single[0].document_id): strong_candidate})

    multiple = select_reference_hits(
        [
            make_hit(title="센디 차량", slug="센디-차량-d1", content_text="차량 문서 1."),
            make_hit(title="센디 차량 (1)", slug="센디-차량-d2", content_text="차량 문서 2."),
        ],
        limit=2,
    )
    candidates = {
        str(reference.document_id): ReferenceCandidate(
            reference=reference,
            stage_rank=0,
            score=4.0,
            family_key="센디 차량",
            order_index=index,
        )
        for index, reference in enumerate(multiple)
    }

    assert _references_have_sufficient_grounding(multiple, candidates)


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
        assert getattr(payload, "doc_type") is None
        assert getattr(payload, "owner_team") is None
        return SearchResponse(query="Transport Delivery operations", hits=hits)

    class FakeGenerator:
        async def generate_body(self, *, topic: str, domain: str | None, references: list[object], validation_feedback: str | None = None) -> str:
            assert topic == "Transport"
            assert domain == "Delivery operations"
            assert len(references) == 2
            assert validation_feedback is None
            return valid_body(open_questions="- Which sub-domains should be excluded from this definition?")

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return []

    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
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
async def test_generate_definition_draft_retries_once_after_validation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = [
        make_hit(title="Transport Overview", slug="transport-overview", content_text="Transport overview."),
        make_hit(title="Carrier Playbook", slug="carrier-playbook", content_text="Transport carrier playbook."),
    ]

    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="Transport", hits=hits)

    class FakeGenerator:
        def __init__(self) -> None:
            self.validation_feedbacks: list[str | None] = []

        async def generate_body(
            self,
            *,
            topic: str,
            domain: str | None,
            references: list[object],
            validation_feedback: str | None = None,
        ) -> str:
            self.validation_feedbacks.append(validation_feedback)
            if len(self.validation_feedbacks) == 1:
                return valid_body(details_citation="[9]")
            return valid_body()

    fake_generator = FakeGenerator()
    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return []

    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )
    monkeypatch.setattr(document_drafts, "get_definition_draft_generator", lambda: fake_generator)

    result = await document_drafts.generate_definition_draft(
        object(),
        GenerateDefinitionDraftRequest(topic="Transport"),
    )

    assert result.slug == "transport"
    assert fake_generator.validation_feedbacks[0] is None
    assert fake_generator.validation_feedbacks[1] == "Draft cites references that do not exist: 9."


@pytest.mark.asyncio
async def test_generate_definition_draft_falls_back_when_validation_fails_after_retry_but_grounding_is_strong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hits = [
        make_hit(title="Transport Overview", slug="transport-overview", content_text="Transport overview."),
        make_hit(title="Carrier Playbook", slug="carrier-playbook", content_text="Transport carrier playbook."),
    ]

    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="Transport", hits=hits)

    class FakeGenerator:
        async def generate_body(
            self,
            *,
            topic: str,
            domain: str | None,
            references: list[object],
            validation_feedback: str | None = None,
        ) -> str:
            return valid_body(details_citation="[9]")

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return []

    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )
    monkeypatch.setattr(document_drafts, "get_definition_draft_generator", lambda: FakeGenerator())

    result = await document_drafts.generate_definition_draft(
        object(),
        GenerateDefinitionDraftRequest(topic="Transport"),
    )

    assert "Transport is a concept grounded in the current corpus" in result.markdown
    assert result.references[0].document_slug == "transport-overview"


@pytest.mark.asyncio
async def test_generate_definition_draft_repairs_missing_citations_after_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = [
        make_hit(title="센디 차량", slug="센디-차량-d1eb3f3193", content_text="센디 차량은 차량 종류와 옵션 정보를 정리한 문서입니다."),
        make_hit(title="다마스, 라보", slug="다마스-라보-926d876185", content_text="차량 종류와 옵션별 제약을 정리합니다."),
    ]

    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="센디 차량 분류", hits=hits)

    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return hits

    class FakeGenerator:
        async def generate_body(
            self,
            *,
            topic: str,
            domain: str | None,
            references: list[object],
            validation_feedback: str | None = None,
        ) -> str:
            return (
                "## Definition\n"
                "센디 차량은 차량 종류와 옵션을 정리한 기준 문서입니다. [1]\n\n"
                "## How This Term Is Used Here\n"
                "운송 화면에서는 차량 종류와 옵션 선택에 이 용어를 사용합니다.\n\n"
                "## Supporting Details\n"
                "- 차종별 제약과 옵션 조합을 함께 확인합니다.\n\n"
                "## Open Questions\n"
                "- 어떤 차종 설명을 더 추가할까요?"
            )

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )
    monkeypatch.setattr(document_drafts, "get_definition_draft_generator", lambda: FakeGenerator())

    result = await document_drafts.generate_definition_draft(
        object(),
        GenerateDefinitionDraftRequest(topic="센디 차량", domain="차량 분류"),
    )

    assert result.references[0].document_slug == "센디-차량-d1eb3f3193"
    assert "운송 화면에서는 차량 종류와 옵션 선택에 이 용어를 사용합니다. [1]" in result.markdown


@pytest.mark.asyncio
async def test_generate_definition_draft_raises_when_no_references(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="Transport", hits=[])

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return []

    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )

    with pytest.raises(DefinitionDraftNotFoundError):
        await document_drafts.generate_definition_draft(object(), GenerateDefinitionDraftRequest(topic="Transport"))


@pytest.mark.asyncio
async def test_generate_definition_draft_raises_when_hybrid_hits_are_irrelevant(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(
            query="센디 차량 분류",
            hits=[make_hit(title="Codex Slug Review Conflict", slug="codexslugreviewdoc", content_text="Second body for conflict handling.")],
        )

    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return []

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )

    with pytest.raises(DefinitionDraftNotFoundError):
        await document_drafts.generate_definition_draft(
            object(),
            GenerateDefinitionDraftRequest(topic="센디 차량", domain="차량 분류", owner_team="platform"),
        )


@pytest.mark.asyncio
async def test_generate_definition_draft_prefers_exact_topic_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    hybrid_hits = [
        make_hit(title="Broad Product Doc", slug="broad-product-doc", content_text="Broad overview."),
        make_hit(title="Other Product Doc", slug="other-product-doc", content_text="Other overview."),
    ]
    exact_hits = [
        make_hit(title="센디 차량", slug="센디-차량-d1eb3f3193", section_title="센디 차량", content_text="정확한 차량 정의."),
        make_hit(title="센디 차량 (1)", slug="센디-차량-d6992f07d0", section_title="센디 차량", content_text="정확한 차량 정의 보완."),
    ]

    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="센디 차량 분류", hits=hybrid_hits)

    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return exact_hits

    class FakeGenerator:
        async def generate_body(self, *, topic: str, domain: str | None, references: list[object], validation_feedback: str | None = None) -> str:
            assert references[0].document_slug == "센디-차량-d1eb3f3193"
            return (
                "## Definition\n"
                "센디 차량은 차량 분류 기준을 정리한 문서입니다. [1]\n\n"
                "## How This Term Is Used Here\n"
                "센디 차량이라는 용어는 화주와 운영 화면에서 차량 선택 기준으로 사용됩니다. [1][2]\n\n"
                "## Supporting Details\n"
                "- 차량 옵션과 톤수 기준이 같은 문서에 정리되어 있습니다. [1][2]\n\n"
                "## Open Questions\n"
                "- 어떤 분류 기준을 더 명확히 설명해야 할까요?"
            )

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=4),
    )
    monkeypatch.setattr(document_drafts, "get_definition_draft_generator", lambda: FakeGenerator())

    result = await document_drafts.generate_definition_draft(
        object(),
        GenerateDefinitionDraftRequest(topic="센디 차량", domain="차량 분류"),
    )

    assert result.references[0].document_slug == "센디-차량-d1eb3f3193"
    assert result.references[1].document_slug == "센디-차량-d6992f07d0"


@pytest.mark.asyncio
async def test_generate_definition_draft_uses_only_exact_references_when_exact_matches_are_sufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hybrid_hits = [
        make_hit(title="Broad Product Doc", slug="broad-product-doc", content_text="Broad overview."),
        make_hit(title="Other Product Doc", slug="other-product-doc", content_text="Other overview."),
    ]
    exact_hits = [
        make_hit(title="센디 차량", slug="센디-차량-d1eb3f3193", section_title="센디 차량", content_text="정확한 차량 정의."),
        make_hit(title="센디 차량", slug="센디-차량-d6992f07d0", section_title="센디 차량", content_text="차량 옵션 정의."),
        make_hit(title="센디 차량 (1)", slug="센디-차량-1-724a1ea1bc", section_title="센디 차량", content_text="차량 분류 테이블."),
    ]

    async def fake_hybrid_search(_session: object, _payload: object) -> SearchResponse:
        return SearchResponse(query="센디 차량 분류", hits=hybrid_hits)

    async def fake_fetch_exact_reference_hits(*_args: object, **_kwargs: object) -> list[SearchHit]:
        return exact_hits

    class FakeGenerator:
        async def generate_body(self, *, topic: str, domain: str | None, references: list[object], validation_feedback: str | None = None) -> str:
            assert [reference.document_slug for reference in references] == [
                "센디-차량-d1eb3f3193",
                "센디-차량-d6992f07d0",
                "센디-차량-1-724a1ea1bc",
            ]
            return valid_body(details_citation="[3]")

    monkeypatch.setattr(document_drafts, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(document_drafts, "fetch_exact_reference_hits", fake_fetch_exact_reference_hits)
    monkeypatch.setattr(
        document_drafts,
        "get_settings",
        lambda: SimpleNamespace(generation_search_limit=6, generation_reference_limit=8),
    )
    monkeypatch.setattr(document_drafts, "get_definition_draft_generator", lambda: FakeGenerator())

    result = await document_drafts.generate_definition_draft(
        object(),
        GenerateDefinitionDraftRequest(topic="센디 차량", domain="차량 분류"),
    )

    assert [reference.document_slug for reference in result.references] == [
        "센디-차량-d1eb3f3193",
        "센디-차량-d6992f07d0",
        "센디-차량-1-724a1ea1bc",
    ]
