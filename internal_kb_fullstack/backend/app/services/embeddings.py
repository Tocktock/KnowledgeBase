from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import tiktoken
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class RemoteEmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.embedding_api_key or None,
            base_url=self.settings.embedding_base_url or None,
            timeout=self.settings.embedding_timeout_seconds,
        )
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def batch_texts(self, texts: Iterable[str]) -> list[list[str]]:
        batches: list[list[str]] = []
        current_batch: list[str] = []
        current_tokens = 0

        for text in texts:
            token_count = self.count_tokens(text)
            if token_count == 0:
                continue
            if token_count > self.settings.embedding_max_input_tokens:
                raise ValueError(
                    f"Single input exceeds embedding limit: {token_count} > {self.settings.embedding_max_input_tokens}"
                )
            if (
                current_batch
                and (
                    len(current_batch) >= self.settings.embedding_batch_size
                    or current_tokens + token_count > self.settings.embedding_request_max_total_tokens
                )
            ):
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            current_batch.append(text)
            current_tokens += token_count

        if current_batch:
            batches.append(current_batch)
        return batches

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        kwargs: dict[str, object] = {
            "model": self.settings.embedding_model,
            "input": texts,
            "encoding_format": "float",
        }
        if self.settings.embedding_model.startswith("text-embedding-3"):
            kwargs["dimensions"] = self.settings.embedding_dimensions
        response = await self.client.embeddings.create(**kwargs)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for batch in self.batch_texts(texts):
            results.extend(await self._embed_batch(batch))
        return results

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]


@lru_cache(maxsize=1)
def get_embedding_service() -> RemoteEmbeddingService:
    return RemoteEmbeddingService()
