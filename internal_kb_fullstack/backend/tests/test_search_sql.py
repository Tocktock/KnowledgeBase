from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.search import SearchRequest
from app.services import search as search_service
from app.services.search import _assemble_concept_hits, current_chunk_filters_sql, query_vector_sql


def test_query_vector_sql_inlines_pgvector_cast() -> None:
    sql = query_vector_sql([0.5, -1.25], 1024)

    assert sql == "CAST('[0.50000000,-1.25000000]' AS vector(1024))"


def test_current_chunk_filters_sql_omits_unset_filters() -> None:
    sql, params = current_chunk_filters_sql(SearchRequest(query="robots"))

    assert sql == ""
    assert params == {}


def test_current_chunk_filters_sql_includes_only_present_filters() -> None:
    sql, params = current_chunk_filters_sql(
        SearchRequest(query="robots", doc_type="spec", owner_team="platform")
    )

    assert sql == "\n              AND d.doc_type = :doc_type\n              AND d.owner_team = :owner_team"
    assert params == {"doc_type": "spec", "owner_team": "platform"}


@pytest.mark.asyncio
async def test_assemble_concept_hits_excludes_evidence_only_supports(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_fetch_canonical_glossary_hit(_session, *, concept, workspace_id=None):
        assert concept.display_term == "용어검증엔진"
        assert workspace_id is None
        return None

    async def fake_get_concept_support_hits(
        _session,
        _concept_id,
        *,
        workspace_id=None,
        limit,
        owner_team=None,
        doc_type=None,
        source_system=None,
        include_evidence_only=True,
    ):
        captured.update(
            {
                "limit": limit,
                "owner_team": owner_team,
                "doc_type": doc_type,
                "source_system": source_system,
                "include_evidence_only": include_evidence_only,
                "workspace_id": workspace_id,
            }
        )
        return []

    monkeypatch.setattr(search_service, "_fetch_canonical_glossary_hit", fake_fetch_canonical_glossary_hit)
    monkeypatch.setattr(search_service, "get_concept_support_hits", fake_get_concept_support_hits)

    hits, canonical_slug = await _assemble_concept_hits(
        object(),
        payload=SearchRequest(query="용어검증엔진", limit=5, owner_team="platform", doc_type="knowledge"),
        concept=SimpleNamespace(
            id=uuid4(),
            display_term="용어검증엔진",
            canonical_document_id=None,
            support_doc_count=2,
        ),
    )

    assert hits == []
    assert canonical_slug is None
    assert captured == {
        "limit": 20,
        "owner_team": "platform",
        "doc_type": "knowledge",
        "source_system": None,
        "include_evidence_only": False,
        "workspace_id": None,
    }
