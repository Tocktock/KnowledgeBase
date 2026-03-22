from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db_session
from app.schemas.search import SearchExplainResponse, SearchRequest, SearchResponse
from app.services.search import explain_search, search_documents

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_route(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    return await search_documents(session, payload)


@router.post("/explain", response_model=SearchExplainResponse)
async def explain_search_route(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SearchExplainResponse:
    return await explain_search(session, payload)
