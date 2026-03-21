from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.utils import normalize_whitespace, slugify
from app.schemas.documents import (
    DefinitionDraftReference,
    GenerateDefinitionDraftRequest,
    GenerateDefinitionDraftResponse,
)
from app.schemas.search import SearchHit, SearchRequest
from app.services.search import hybrid_search


class DefinitionDraftError(RuntimeError):
    pass


class DefinitionDraftConfigError(DefinitionDraftError):
    pass


class DefinitionDraftNotFoundError(DefinitionDraftError):
    pass


class DefinitionDraftGenerationError(DefinitionDraftError):
    pass

def build_definition_query(topic: str, domain: str | None = None) -> str:
    parts = [topic.strip()]
    if domain and domain.strip():
        parts.append(domain.strip())
    return " ".join(parts)


def _trim_excerpt(text: str, *, limit: int = 420) -> str:
    normalized = normalize_whitespace(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def select_reference_hits(hits: Iterable[SearchHit], *, limit: int) -> list[DefinitionDraftReference]:
    references: list[DefinitionDraftReference] = []
    seen: set[tuple[str, str | None, tuple[str, ...], str]] = set()

    for hit in hits:
        excerpt = _trim_excerpt(hit.content_text)
        dedupe_key = (
            str(hit.document_id),
            hit.section_title,
            tuple(hit.heading_path),
            excerpt,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        references.append(
            DefinitionDraftReference(
                index=len(references) + 1,
                document_id=hit.document_id,
                document_title=hit.document_title,
                document_slug=hit.document_slug,
                source_system=hit.source_system,
                source_url=hit.source_url,
                section_title=hit.section_title,
                heading_path=hit.heading_path,
                excerpt=excerpt,
            )
        )
        if len(references) >= limit:
            break

    return references


def _reference_location(reference: DefinitionDraftReference) -> str | None:
    parts = [part for part in [reference.section_title, *reference.heading_path] if part]
    if not parts:
        return None
    return " > ".join(parts)


def build_reference_section(references: list[DefinitionDraftReference]) -> str:
    lines = ["## References", ""]
    for reference in references:
        lines.append(f"{reference.index}. [{reference.document_title}](/docs/{reference.document_slug})")
        location = _reference_location(reference)
        if location:
            lines.append(f"   - Location: {location}")
        lines.append(f"   - Source system: {reference.source_system}")
        if reference.source_url:
            lines.append(f"   - Source: `{reference.source_url}`")
        lines.append(f"   - Excerpt: {reference.excerpt}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _normalize_generated_body(markdown: str) -> str:
    body = normalize_whitespace(markdown)
    body = re.sub(r"^# .+\n+", "", body, count=1)
    body = re.split(r"\n## References\b", body, maxsplit=1)[0]
    return body.strip()


def build_reference_prompt(references: list[DefinitionDraftReference]) -> str:
    lines: list[str] = []
    for reference in references:
        lines.append(f"[{reference.index}] {reference.document_title}")
        lines.append(f"slug: {reference.document_slug}")
        lines.append(f"source_system: {reference.source_system}")
        if reference.source_url:
            lines.append(f"source_url: {reference.source_url}")
        location = _reference_location(reference)
        if location:
            lines.append(f"location: {location}")
        lines.append(f"excerpt: {reference.excerpt}")
        lines.append("")
    return "\n".join(lines).strip()


class DefinitionDraftGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.generation_api_key or self.settings.embedding_api_key or None,
            base_url=self.settings.generation_base_url or self.settings.embedding_base_url or None,
            timeout=self.settings.generation_timeout_seconds,
        )

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def generate_body(
        self,
        *,
        topic: str,
        domain: str | None,
        references: list[DefinitionDraftReference],
    ) -> str:
        if not self.settings.generation_model:
            raise DefinitionDraftConfigError(
                "GENERATION_MODEL is not configured. Set a chat-capable model before generating drafts."
            )

        response = await self.client.chat.completions.create(
            model=self.settings.generation_model,
            temperature=self.settings.generation_temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write editable knowledge-base definition drafts grounded only in provided references. "
                        "Respond in markdown body only. Do not include a top-level title. Do not include a References "
                        "section. Use inline citations like [1] and only cite provided references. If the evidence is "
                        "incomplete or conflicting, say so explicitly instead of inventing facts."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic.strip()}\n"
                        f"Domain/context: {(domain or 'not specified').strip()}\n\n"
                        "Write a concise but useful draft with these sections:\n"
                        "## Definition\n"
                        "## How This Term Is Used Here\n"
                        "## Supporting Details\n"
                        "## Open Questions\n\n"
                        "Use the same primary language as the topic/context request, preserving domain terms as written.\n\n"
                        f"References:\n{build_reference_prompt(references)}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise DefinitionDraftGenerationError("The model returned an empty draft.")

        body = _normalize_generated_body(content)
        if not body:
            raise DefinitionDraftGenerationError("The generated draft body was empty after normalization.")
        return body


@lru_cache(maxsize=1)
def get_definition_draft_generator() -> DefinitionDraftGenerator:
    return DefinitionDraftGenerator()


async def generate_definition_draft(
    session: AsyncSession,
    payload: GenerateDefinitionDraftRequest,
) -> GenerateDefinitionDraftResponse:
    settings = get_settings()
    search_limit = payload.search_limit or settings.generation_search_limit
    reference_limit = payload.reference_limit or settings.generation_reference_limit
    query = build_definition_query(payload.topic, payload.domain)

    search_response = await hybrid_search(
        session,
        SearchRequest(
            query=query,
            limit=search_limit,
            doc_type=payload.doc_type,
            source_system=payload.source_system,
            owner_team=payload.owner_team,
        ),
    )
    references = select_reference_hits(search_response.hits, limit=reference_limit)
    if not references:
        raise DefinitionDraftNotFoundError("No relevant references were found for this topic.")

    generator = get_definition_draft_generator()
    body = await generator.generate_body(topic=payload.topic, domain=payload.domain, references=references)
    title = payload.topic.strip()
    lines = [f"# {title}", ""]
    if payload.domain and payload.domain.strip():
        lines.extend([f"> Domain: {payload.domain.strip()}", ""])
    lines.extend([body, "", build_reference_section(references)])

    return GenerateDefinitionDraftResponse(
        title=title,
        slug=slugify(title),
        query=query,
        markdown="\n".join(lines).strip(),
        references=references,
    )
