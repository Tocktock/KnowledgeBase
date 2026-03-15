from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import tiktoken

from app.core.config import get_settings
from app.core.utils import normalize_whitespace, sha256_text
from app.services.parser import DocumentParser


@dataclass(slots=True)
class ChunkPayload:
    chunk_index: int
    section_title: str | None
    heading_path: list[str]
    content_text: str
    content_tokens: int
    content_hash: str
    metadata: dict[str, Any]


class TokenAwareChunker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _token_window_split(self, text: str) -> list[str]:
        text = normalize_whitespace(text)
        if not text:
            return []
        tokens = self.encoding.encode(text)
        if len(tokens) <= self.settings.chunk_max_tokens:
            return [text]

        step = max(1, self.settings.chunk_max_tokens - self.settings.chunk_overlap_tokens)
        windows: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + self.settings.chunk_max_tokens, len(tokens))
            window = self.encoding.decode(tokens[start:end]).strip()
            if window:
                windows.append(normalize_whitespace(window))
            if end >= len(tokens):
                break
            start += step
        return windows

    def _split_markdown_sections(self, markdown_text: str) -> list[tuple[str | None, list[str], str]]:
        sections: list[tuple[str | None, list[str], str]] = []
        heading_path: list[str] = []
        section_title: str | None = None
        current_lines: list[str] = []

        def flush() -> None:
            if not current_lines:
                return
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((section_title, heading_path.copy(), body))
            current_lines.clear()

        for line in markdown_text.splitlines():
            match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if match:
                flush()
                level = len(match.group(1))
                title = normalize_whitespace(match.group(2))
                heading_path[:] = heading_path[: level - 1] + [title]
                section_title = title
            else:
                current_lines.append(line)

        flush()
        if not sections and markdown_text.strip():
            sections.append((None, [], markdown_text.strip()))
        return sections

    def _paragraph_chunks(self, text: str) -> list[str]:
        paragraphs = [normalize_whitespace(p) for p in re.split(r"\n{2,}", text) if normalize_whitespace(p)]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)
            if paragraph_tokens > self.settings.chunk_max_tokens:
                if current_parts:
                    chunks.append(normalize_whitespace("\n\n".join(current_parts)))
                    current_parts = []
                    current_tokens = 0
                chunks.extend(self._token_window_split(paragraph))
                continue

            if current_parts and current_tokens + paragraph_tokens > self.settings.chunk_target_tokens:
                emitted = normalize_whitespace("\n\n".join(current_parts))
                chunks.append(emitted)
                overlap_tokens = self.encoding.encode(emitted)[-self.settings.chunk_overlap_tokens :]
                overlap_text = normalize_whitespace(self.encoding.decode(overlap_tokens)) if overlap_tokens else ""
                current_parts = [part for part in [overlap_text, paragraph] if part]
                current_tokens = self.count_tokens("\n\n".join(current_parts))
            else:
                current_parts.append(paragraph)
                current_tokens += paragraph_tokens

        if current_parts:
            chunks.append(normalize_whitespace("\n\n".join(current_parts)))

        return [chunk for chunk in chunks if chunk]

    def chunk(self, *, content_type: str, content: str, metadata: dict[str, Any] | None = None) -> list[ChunkPayload]:
        metadata = metadata or {}
        chunks: list[ChunkPayload] = []
        chunk_index = 0

        if content_type == "markdown":
            for section_title, heading_path, section_markdown in self._split_markdown_sections(content):
                section_text = DocumentParser.markdown_to_text(section_markdown)
                for piece in self._paragraph_chunks(section_text):
                    chunks.append(
                        ChunkPayload(
                            chunk_index=chunk_index,
                            section_title=section_title,
                            heading_path=heading_path,
                            content_text=piece,
                            content_tokens=self.count_tokens(piece),
                            content_hash=sha256_text(piece),
                            metadata=metadata,
                        )
                    )
                    chunk_index += 1
            return chunks

        normalized = normalize_whitespace(content)
        for piece in self._paragraph_chunks(normalized):
            chunks.append(
                ChunkPayload(
                    chunk_index=chunk_index,
                    section_title=None,
                    heading_path=[],
                    content_text=piece,
                    content_tokens=self.count_tokens(piece),
                    content_hash=sha256_text(piece),
                    metadata=metadata,
                )
            )
            chunk_index += 1
        return chunks
