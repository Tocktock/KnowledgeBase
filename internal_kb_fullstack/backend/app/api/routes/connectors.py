from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user, get_optional_authenticated_user
from app.db.engine import get_db_session
from app.schemas.auth import OAuthStartResponse
from app.schemas.connectors import (
    ConnectorBrowseResponse,
    ConnectorConnectionSummary,
    ConnectorListResponse,
    ConnectorOAuthCallbackResponse,
    ConnectorReadinessResponse,
    ConnectorResourceCreateRequest,
    ConnectorResourceSummary,
    ConnectorResourceUpdateRequest,
    ConnectorSourceItemSummary,
    ConnectorUpdateRequest,
)
from app.schemas.jobs import JobSummary
from app.services.auth import AuthenticatedUser
from app.services.connectors import (
    ConnectorError,
    ConnectorForbiddenError,
    ConnectorNotFoundError,
    browse_connection,
    complete_provider_oauth,
    create_resource,
    delete_connection,
    delete_resource,
    get_connection_detail,
    get_connectors_readiness,
    list_connections,
    list_source_items,
    import_notion_export_resource,
    request_resource_sync,
    start_provider_oauth,
    update_connection,
    update_resource,
)

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


def _raise_connector_http_error(exc: ConnectorError) -> None:
    if isinstance(exc, ConnectorForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, ConnectorNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/readiness", response_model=ConnectorReadinessResponse)
async def connectors_readiness_route(
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> ConnectorReadinessResponse:
    return await get_connectors_readiness(session, auth_user)


@router.get("", response_model=ConnectorListResponse)
async def list_connections_route(
    scope: str = Query(default="workspace"),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorListResponse:
    return await list_connections(session, auth_user, scope=scope)


@router.post("/{provider}/oauth/start", response_model=OAuthStartResponse)
async def start_provider_oauth_route(
    provider: str,
    owner_scope: str = Query(default="workspace"),
    return_to: str = Query(default="/connectors"),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> OAuthStartResponse:
    try:
        payload = await start_provider_oauth(
            session,
            auth_user,
            provider=provider,
            owner_scope=owner_scope,
            return_path=return_to,
        )
    except ConnectorError as exc:
        _raise_connector_http_error(exc)
    return OAuthStartResponse(**payload)


@router.get("/{provider}/oauth/callback", response_model=ConnectorOAuthCallbackResponse)
async def complete_provider_oauth_route(
    provider: str,
    state: str,
    code: str,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorOAuthCallbackResponse:
    try:
        return await complete_provider_oauth(session, auth_user, provider=provider, state=state, code=code)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.get("/{connection_id}", response_model=ConnectorConnectionSummary)
async def get_connection_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorConnectionSummary:
    try:
        return await get_connection_detail(session, auth_user, connection_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.patch("/{connection_id}", response_model=ConnectorConnectionSummary)
async def update_connection_route(
    connection_id: UUID,
    payload: ConnectorUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorConnectionSummary:
    try:
        return await update_connection(session, auth_user, connection_id, payload)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    try:
        await delete_connection(session, auth_user, connection_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.get("/{connection_id}/browse", response_model=ConnectorBrowseResponse)
async def browse_connection_route(
    connection_id: UUID,
    kind: str | None = Query(default=None),
    query: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    parent_id: str | None = Query(default=None),
    container_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorBrowseResponse:
    try:
        return await browse_connection(
            session,
            auth_user,
            connection_id,
            kind=kind,
            query=query,
            cursor=cursor,
            parent_id=parent_id,
            container_id=container_id,
        )
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.get("/{connection_id}/resources", response_model=list[ConnectorResourceSummary])
async def list_resources_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[ConnectorResourceSummary]:
    try:
        connection = await get_connection_detail(session, auth_user, connection_id)
        return connection.resources
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.post("/{connection_id}/resources", response_model=ConnectorResourceSummary, status_code=status.HTTP_201_CREATED)
async def create_resource_route(
    connection_id: UUID,
    payload: ConnectorResourceCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorResourceSummary:
    try:
        return await create_resource(session, auth_user, connection_id, payload)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.post(
    "/{connection_id}/resources/upload",
    response_model=ConnectorResourceSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resource_route(
    connection_id: UUID,
    name: str = Form(...),
    visibility_scope: str = Form(default="evidence_only"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorResourceSummary:
    try:
        return await import_notion_export_resource(
            session,
            auth_user,
            connection_id,
            name=name,
            filename=file.filename or "notion-export.zip",
            content_bytes=await file.read(),
            visibility_scope=visibility_scope,
        )
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.patch("/{connection_id}/resources/{resource_id}", response_model=ConnectorResourceSummary)
async def update_resource_route(
    connection_id: UUID,
    resource_id: UUID,
    payload: ConnectorResourceUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorResourceSummary:
    try:
        return await update_resource(session, auth_user, connection_id, resource_id, payload)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.delete("/{connection_id}/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource_route(
    connection_id: UUID,
    resource_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    try:
        await delete_resource(session, auth_user, connection_id, resource_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.post("/{connection_id}/resources/{resource_id}/sync", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def request_resource_sync_route(
    connection_id: UUID,
    resource_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JobSummary:
    try:
        return await request_resource_sync(session, auth_user, connection_id, resource_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.get("/{connection_id}/items", response_model=list[ConnectorSourceItemSummary])
async def list_source_items_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[ConnectorSourceItemSummary]:
    try:
        return await list_source_items(session, auth_user, connection_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)
