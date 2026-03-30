from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_authenticated_user
from app.db.engine import get_db_session
from app.schemas.search import SearchExplainResponse, SearchRequest, SearchResponse
from app.services.auth import AuthenticatedUser
from app.services.search import explain_search, search_documents
from app.services.workspace import resolve_read_workspace_id

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_route(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> SearchResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    return await search_documents(session, payload, workspace_id=workspace_id)


@router.post("/explain", response_model=SearchExplainResponse)
async def explain_search_route(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> SearchExplainResponse:
    workspace_id = await resolve_read_workspace_id(session, auth_user)
    return await explain_search(session, payload, workspace_id=workspace_id)
