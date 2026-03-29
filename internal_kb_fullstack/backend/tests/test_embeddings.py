from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.services.embeddings import RemoteEmbeddingService


@pytest.mark.asyncio
async def test_embed_many_preserves_batch_order_with_concurrency() -> None:
    service = RemoteEmbeddingService.__new__(RemoteEmbeddingService)
    service.settings = SimpleNamespace(
        embedding_batch_size=2,
        embedding_batch_concurrency=2,
        embedding_request_max_total_tokens=10,
        embedding_max_input_tokens=10,
    )
    service.count_tokens = lambda text: 1

    active = 0
    max_active = 0

    async def fake_embed_batch(texts: list[str]) -> list[list[float]]:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.02 if texts[0] == "a" else 0.01)
        active -= 1
        return [[float(ord(text[0]))] for text in texts]

    service._embed_batch = fake_embed_batch

    result = await RemoteEmbeddingService.embed_many(service, ["a", "b", "c", "d", "e"])

    assert result == [[97.0], [98.0], [99.0], [100.0], [101.0]]
    assert max_active == 2
