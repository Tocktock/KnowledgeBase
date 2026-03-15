from __future__ import annotations

import pytest

from app.db import engine


class DummySession:
    pass


class DummySessionContext:
    def __init__(self, session: DummySession) -> None:
        self.session = session

    async def __aenter__(self) -> DummySession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class DummySessionFactory:
    def __init__(self, session: DummySession) -> None:
        self.session = session
        self.call_count = 0

    def __call__(self) -> DummySessionContext:
        self.call_count += 1
        return DummySessionContext(self.session)


@pytest.mark.asyncio
async def test_get_db_session_opens_session_from_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    factory = DummySessionFactory(session)
    monkeypatch.setattr(engine, "get_session_factory", lambda: factory)

    iterator = engine.get_db_session()
    yielded = await anext(iterator)

    assert yielded is session
    assert factory.call_count == 1

    with pytest.raises(StopAsyncIteration):
        await anext(iterator)
