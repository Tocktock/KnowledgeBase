from app.services.wiki_graph import extract_heading_items, extract_internal_links, extract_internal_slugs



def test_extract_internal_links_supports_wiki_and_docs_links() -> None:
    markdown = """
# 배포

[[Runbook|배포 런북]]
[운영 문서](/docs/ops-guide#rollout)
"""
    links = extract_internal_links(markdown)

    assert [link.target_slug for link in links] == ["runbook", "ops-guide"]
    assert links[0].link_text == "배포 런북"
    assert links[1].target_anchor == "rollout"



def test_extract_internal_slugs_preserves_order_and_uniqueness() -> None:
    markdown = "[[A]] [[a|again]] [other](/docs/b) [[B]]"
    assert extract_internal_slugs(markdown) == ["a", "b"]



def test_extract_heading_items_generates_stable_ids() -> None:
    markdown = "# 첫 제목\n\n## 두 번째 섹션\n"
    headings = extract_heading_items(markdown)

    assert headings == [
        {"title": "첫 제목", "id": "첫-제목"},
        {"title": "두 번째 섹션", "id": "두-번째-섹션"},
    ]
