from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db_session
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search import hybrid_search

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_route(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    return await hybrid_search(session, payload)
