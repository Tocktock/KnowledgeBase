from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from scripts import import_sample_corpus


def test_select_corpus_files_prefers_all_csv_variant(tmp_path: Path) -> None:
    root = tmp_path / "sendy"
    root.mkdir()
    (root / "Doc abcdef1234.md").write_text("# Doc", encoding="utf-8")
    (root / "Table 1234567890.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (root / "Table 1234567890_all.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (root / ".DS_Store").write_text("", encoding="utf-8")

    selected = [path.name for path in import_sample_corpus.select_corpus_files(root)]

    assert selected == ["Doc abcdef1234.md", "Table 1234567890_all.csv"]


def test_build_corpus_file_extracts_title_slug_and_owner_team(tmp_path: Path) -> None:
    root = tmp_path / "sendy"
    path = root / "Product Home" / "Product Team" / "화주 스쿼드" / "센디 차량 (1) 8d9f3e0772904114908cb06205a2643f_all.csv"
    path.parent.mkdir(parents=True)
    path.write_text("title,body\n", encoding="utf-8")

    corpus_file = import_sample_corpus.build_corpus_file(root, path)

    assert corpus_file.relative_path == "Product Home/Product Team/화주 스쿼드/센디 차량 (1) 8d9f3e0772904114908cb06205a2643f_all.csv"
    assert corpus_file.title == "센디 차량 (1)"
    assert corpus_file.slug == "센디-차량-1-8d9f3e0772"
    assert corpus_file.doc_type == "data"
    assert corpus_file.content_type == "text"
    assert corpus_file.owner_team == "product"


@pytest.mark.asyncio
async def test_import_corpus_uses_source_external_id_as_provenance_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "sendy"
    path = root / "Product Home" / "Spec abcdef1234.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Spec", encoding="utf-8")
    captured = {}

    class SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(import_sample_corpus, "get_session_factory", lambda: (lambda: SessionContext()))

    async def fake_ingest_document(_session, payload):
        captured["payload"] = payload
        return SimpleNamespace(unchanged=False)

    monkeypatch.setattr(import_sample_corpus, "ingest_document", fake_ingest_document)

    result = await import_sample_corpus.import_corpus(
        root=root,
        source_system="notion-export",
        import_batch="sample-data-sendy-knowledge",
        refresh_glossary=False,
        skip_if_detected=False,
        detection_threshold=1,
    )

    payload = captured["payload"]
    assert result["imported"] == 1
    assert payload.source_external_id == "Product Home/Spec abcdef1234.md"
    assert payload.source_url is None
