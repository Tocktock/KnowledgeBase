from app.services.chunking import TokenAwareChunker


def test_markdown_chunker_preserves_headings() -> None:
    chunker = TokenAwareChunker()
    chunks = chunker.chunk(
        content_type="markdown",
        content="# 제목\n\n첫 문단입니다.\n\n## 세부\n\n두 번째 문단입니다.",
    )
    assert chunks
    assert chunks[0].heading_path[0] == "제목"


def test_text_chunker_splits_long_text() -> None:
    chunker = TokenAwareChunker()
    long_text = "문장입니다. " * 1000
    chunks = chunker.chunk(content_type="text", content=long_text)
    assert len(chunks) > 1
