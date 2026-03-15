from __future__ import annotations

import asyncio

from app.db.engine import get_session_factory
from app.services.worker import run_worker_loop


async def main() -> None:
    await run_worker_loop(get_session_factory())


if __name__ == "__main__":
    asyncio.run(main())
