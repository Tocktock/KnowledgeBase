from app.schemas.search import SearchRequest
from app.services.search import current_chunk_filters_sql, query_vector_sql


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
