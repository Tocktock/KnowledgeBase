from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import markdown as md
from bs4 import BeautifulSoup

from app.core.utils import normalize_whitespace

ContentType = Literal["markdown", "text", "html"]


@dataclass(slots=True)
class ParsedContent:
    content_type: ContentType
    markdown_text: str | None
    plain_text: str


class DocumentParser:
    @staticmethod
    def infer_content_type(filename: str) -> ContentType:
        suffix = Path(filename).suffix.lower()
        if suffix in {".md", ".markdown"}:
            return "markdown"
        if suffix in {".html", ".htm"}:
            return "html"
        return "text"

    @staticmethod
    def markdown_to_text(content: str) -> str:
        html = md.markdown(content)
        text = BeautifulSoup(html, "html.parser").get_text("\n")
        return normalize_whitespace(text)

    @staticmethod
    def html_to_text(content: str) -> str:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text("\n")
        return normalize_whitespace(text)

    @classmethod
    def parse(cls, *, content_type: ContentType, content: str) -> ParsedContent:
        content = normalize_whitespace(content)
        if content_type == "markdown":
            return ParsedContent(
                content_type="markdown",
                markdown_text=content,
                plain_text=cls.markdown_to_text(content),
            )
        if content_type == "html":
            return ParsedContent(
                content_type="html",
                markdown_text=None,
                plain_text=cls.html_to_text(content),
            )
        return ParsedContent(content_type="text", markdown_text=None, plain_text=content)
