from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import EmbeddingJob
from app.services import jobs as jobs_service


class ReindexSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, item: object) -> None:
        self.refreshed.append(item)


def make_document(*, visibility_scope: str = "member_visible"):
    document_id = uuid4()
    revision_id = uuid4()
    now = datetime.now(timezone.utc)
    document = SimpleNamespace(
        id=document_id,
        workspace_id=uuid4(),
        visibility_scope=visibility_scope,
        current_revision_id=revision_id,
    )
    revision = SimpleNamespace(
        id=revision_id,
        document_id=document_id,
        revision_number=1,
        created_at=now,
    )
    return document, revision


@pytest.mark.asyncio
async def test_request_document_reindex_succeeds_for_member_visible_document(monkeypatch: pytest.MonkeyPatch) -> None:
    session = ReindexSession()
    document, revision = make_document(visibility_scope="member_visible")
    captured: dict[str, object] = {}
    job = EmbeddingJob(id=uuid4(), document_id=document.id, revision_id=revision.id)

    async def fake_get_document_detail(_session, document_id, *, workspace_id=None, include_evidence_only: bool = False):
        captured.update(
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "include_evidence_only": include_evidence_only,
            }
        )
        return document, revision, []

    async def fake_create_embedding_job(_session, *, document_id, revision_id, priority):
        assert document_id == document.id
        assert revision_id == revision.id
        assert priority == 120
        return job

    monkeypatch.setattr(jobs_service, "get_document_detail", fake_get_document_detail)
    monkeypatch.setattr(jobs_service, "create_embedding_job", fake_create_embedding_job)

    result = await jobs_service.request_document_reindex(
        session,
        document_id=document.id,
        workspace_id=document.workspace_id,
        priority=120,
    )

    assert result is job
    assert captured["include_evidence_only"] is True
    assert session.commit_calls == 1
    assert session.refreshed == [job]


@pytest.mark.asyncio
async def test_request_document_reindex_succeeds_for_evidence_only_document(monkeypatch: pytest.MonkeyPatch) -> None:
    session = ReindexSession()
    document, revision = make_document(visibility_scope="evidence_only")
    job = EmbeddingJob(id=uuid4(), document_id=document.id, revision_id=revision.id)

    async def fake_get_document_detail(_session, _document_id, *, workspace_id=None, include_evidence_only: bool = False):
        assert workspace_id == document.workspace_id
        assert include_evidence_only is True
        return document, revision, []

    async def fake_create_embedding_job(_session, *, document_id, revision_id, priority):
        assert document_id == document.id
        assert revision_id == revision.id
        assert priority == 140
        return job

    monkeypatch.setattr(jobs_service, "get_document_detail", fake_get_document_detail)
    monkeypatch.setattr(jobs_service, "create_embedding_job", fake_create_embedding_job)

    result = await jobs_service.request_document_reindex(
        session,
        document_id=document.id,
        workspace_id=document.workspace_id,
        priority=140,
    )

    assert result is job
    assert session.commit_calls == 1
    assert session.refreshed == [job]


@pytest.mark.asyncio
async def test_request_document_reindex_returns_none_for_wrong_workspace_document(monkeypatch: pytest.MonkeyPatch) -> None:
    session = ReindexSession()
    captured: dict[str, object] = {}

    async def fake_get_document_detail(_session, document_id, *, workspace_id=None, include_evidence_only: bool = False):
        captured.update(
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "include_evidence_only": include_evidence_only,
            }
        )
        return None, None, []

    async def fake_create_embedding_job(*_args, **_kwargs):
        raise AssertionError("create_embedding_job should not be called when the document is unavailable")

    monkeypatch.setattr(jobs_service, "get_document_detail", fake_get_document_detail)
    monkeypatch.setattr(jobs_service, "create_embedding_job", fake_create_embedding_job)

    result = await jobs_service.request_document_reindex(
        session,
        document_id=uuid4(),
        workspace_id=uuid4(),
        priority=90,
    )

    assert result is None
    assert captured["include_evidence_only"] is True
    assert session.commit_calls == 0
    assert session.refreshed == []


@pytest.mark.asyncio
async def test_request_document_reindex_returns_none_when_document_has_no_current_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    session = ReindexSession()
    document, _revision = make_document()

    async def fake_get_document_detail(_session, _document_id, *, workspace_id=None, include_evidence_only: bool = False):
        assert workspace_id == document.workspace_id
        assert include_evidence_only is True
        return document, None, []

    async def fake_create_embedding_job(*_args, **_kwargs):
        raise AssertionError("create_embedding_job should not be called when the document has no current revision")

    monkeypatch.setattr(jobs_service, "get_document_detail", fake_get_document_detail)
    monkeypatch.setattr(jobs_service, "create_embedding_job", fake_create_embedding_job)

    result = await jobs_service.request_document_reindex(
        session,
        document_id=document.id,
        workspace_id=document.workspace_id,
        priority=100,
    )

    assert result is None
    assert session.commit_calls == 0
    assert session.refreshed == []
