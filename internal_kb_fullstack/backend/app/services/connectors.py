from __future__ import annotations

import csv
import io
from collections import deque
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
import pytesseract
from docx import Document as DocxDocument
from openpyxl import load_workbook
from PIL import Image
from pypdf import PdfReader
from pptx import Presentation
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.security import (
    create_code_challenge,
    decrypt_secret,
    encrypt_secret,
    future_utc,
    generate_code_verifier,
    generate_state_token,
)
from app.core.utils import normalize_whitespace, slugify, utcnow
from app.db.models import (
    ConnectorConnection,
    ConnectorOAuthPurpose,
    ConnectorOAuthState,
    ConnectorOwnerScope,
    ConnectorProvider,
    ConnectorSourceItem,
    ConnectorSourceItemStatus,
    ConnectorStatus,
    ConnectorSyncJob,
    ConnectorSyncJobKind,
    ConnectorSyncMode,
    ConnectorSyncTarget,
    ConnectorTargetStatus,
    ConnectorTargetType,
    Document,
    JobStatus,
)
from app.schemas.connectors import (
    ConnectorBrowseItem,
    ConnectorBrowseResponse,
    ConnectorConnectionSummary,
    ConnectorListResponse,
    ConnectorOAuthCallbackResponse,
    ConnectorReadinessResponse,
    ConnectorSourceItemSummary,
    ConnectorTargetCreateRequest,
    ConnectorTargetSummary,
    ConnectorTargetUpdateRequest,
    ConnectorUpdateRequest,
)
from app.schemas.documents import IngestDocumentRequest
from app.schemas.jobs import JobSummary
from app.services.auth import AuthenticatedUser
from app.services.ingest import ingest_document

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_DRIVE_V3 = "https://www.googleapis.com/drive/v3"
CONNECTOR_SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive.readonly"]
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDE_MIME = "application/vnd.google-apps.presentation"
GOOGLE_DRAWING_MIME = "application/vnd.google-apps.drawing"


class ConnectorError(RuntimeError):
    pass


class ConnectorForbiddenError(ConnectorError):
    pass


class ConnectorNotFoundError(ConnectorError):
    pass


@dataclass(slots=True)
class ExtractedContent:
    content_type: str
    content: str
    doc_type: str


def _app_callback_path(path: str) -> str:
    settings = get_settings()
    return f"{settings.app_public_url.rstrip('/')}{path}"


def _safe_return_path(value: str | None) -> str:
    if not value or not value.startswith("/"):
        return "/connectors"
    return value


def _validate_owner_scope(scope: str) -> str:
    if scope not in {ConnectorOwnerScope.shared.value, ConnectorOwnerScope.user.value}:
        raise ConnectorError("Unsupported owner scope.")
    return scope


def _validate_target_type(value: str) -> str:
    if value not in {ConnectorTargetType.folder.value, ConnectorTargetType.shared_drive.value}:
        raise ConnectorError("Unsupported connector target type.")
    return value


def _validate_browse_kind(value: str) -> str:
    if value not in {ConnectorTargetType.folder.value, ConnectorTargetType.shared_drive.value}:
        raise ConnectorError("Unsupported browse kind.")
    return value


def _revision_token(file_meta: dict[str, Any]) -> str:
    version = str(file_meta.get("version") or "")
    modified = str(file_meta.get("modifiedTime") or "")
    checksum = str(file_meta.get("md5Checksum") or "")
    return f"{version}:{modified}:{checksum}"


def _stable_document_slug(title: str, external_id: str) -> str:
    return f"{slugify(title)}-{external_id[:10].lower()}"


def _google_drive_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)


def _ensure_google_drive_configured() -> None:
    if not _google_drive_configured():
        raise ConnectorError("Google Drive OAuth is not configured.")


def _target_summary(target: ConnectorSyncTarget) -> ConnectorTargetSummary:
    return ConnectorTargetSummary(
        id=target.id,
        connection_id=target.connection_id,
        target_type=target.target_type,
        external_id=target.external_id,
        name=target.name,
        include_subfolders=target.include_subfolders,
        sync_mode=target.sync_mode,
        sync_interval_minutes=target.sync_interval_minutes,
        status=target.status,
        last_sync_started_at=target.last_sync_started_at,
        last_sync_completed_at=target.last_sync_completed_at,
        next_auto_sync_at=target.next_auto_sync_at,
        last_sync_summary=dict(target.last_sync_summary or {}),
    )


def _default_sync_schedule_for_scope(owner_scope: str) -> tuple[str, int | None]:
    if owner_scope == ConnectorOwnerScope.shared.value:
        return ConnectorSyncMode.auto.value, 60
    return ConnectorSyncMode.manual.value, None


def _connection_summary(connection: ConnectorConnection, targets: list[ConnectorSyncTarget]) -> ConnectorConnectionSummary:
    return ConnectorConnectionSummary(
        id=connection.id,
        provider=connection.provider,
        owner_scope=connection.owner_scope,
        owner_user_id=connection.owner_user_id,
        display_name=connection.display_name,
        account_email=connection.account_email,
        account_subject=connection.account_subject,
        status=connection.status,
        granted_scopes=list(connection.granted_scopes or []),
        last_validated_at=connection.last_validated_at,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        targets=[_target_summary(target) for target in targets],
    )


def _source_item_summary(item: ConnectorSourceItem) -> ConnectorSourceItemSummary:
    return ConnectorSourceItemSummary(
        id=item.id,
        target_id=item.target_id,
        external_file_id=item.external_file_id,
        mime_type=item.mime_type,
        name=item.name,
        source_url=item.source_url,
        source_revision_id=item.source_revision_id,
        internal_document_id=item.internal_document_id,
        item_status=item.item_status,
        unsupported_reason=item.unsupported_reason,
        error_message=item.error_message,
        last_seen_at=item.last_seen_at,
        last_synced_at=item.last_synced_at,
    )


async def _exchange_google_code(*, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
    _ensure_google_drive_configured()
    settings = get_settings()
    payload = {
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=payload)
    if response.status_code >= 400:
        raise ConnectorError(f"Google token exchange failed: {response.text}")
    return response.json()


async def _refresh_google_token(refresh_token: str) -> dict[str, Any]:
    _ensure_google_drive_configured()
    settings = get_settings()
    payload = {
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=payload)
    if response.status_code >= 400:
        raise ConnectorError(f"Google token refresh failed: {response.text}")
    return response.json()


async def _google_userinfo(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise ConnectorError(f"Google userinfo lookup failed: {response.text}")
    return response.json()


async def _active_access_token(session: AsyncSession, connection: ConnectorConnection) -> str:
    access_token = decrypt_secret(connection.encrypted_access_token)
    refresh_token = decrypt_secret(connection.encrypted_refresh_token)
    expires_at = connection.token_expires_at
    if access_token and expires_at and expires_at > future_utc(seconds=60):
        return access_token
    if not refresh_token:
        connection.status = ConnectorStatus.needs_reauth.value
        await session.commit()
        raise ConnectorError("Connector token refresh is unavailable.")
    token_data = await _refresh_google_token(refresh_token)
    new_access = str(token_data["access_token"])
    connection.encrypted_access_token = encrypt_secret(new_access) or ""
    connection.token_expires_at = future_utc(seconds=int(token_data.get("expires_in", 3600)))
    if token_data.get("refresh_token"):
        connection.encrypted_refresh_token = encrypt_secret(str(token_data["refresh_token"]))
    connection.status = ConnectorStatus.active.value
    connection.last_validated_at = utcnow()
    await session.commit()
    return new_access


async def _google_json(
    session: AsyncSession,
    connection: ConnectorConnection,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    token = await _active_access_token(session, connection)
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            f"{GOOGLE_DRIVE_V3}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise ConnectorError(f"Google Drive request failed: {response.text}")
    return response.json()


async def _google_bytes(
    session: AsyncSession,
    connection: ConnectorConnection,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> bytes:
    token = await _active_access_token(session, connection)
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(
            f"{GOOGLE_DRIVE_V3}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise ConnectorError(f"Google Drive download failed: {response.text}")
    return response.content


async def _get_connection_or_raise(
    session: AsyncSession,
    connection_id: UUID,
    auth_user: AuthenticatedUser,
    *,
    allow_shared_read: bool = True,
) -> ConnectorConnection:
    connection = await session.get(ConnectorConnection, connection_id)
    if connection is None:
        raise ConnectorNotFoundError("Connector not found.")
    if connection.owner_scope == ConnectorOwnerScope.shared.value:
        if not allow_shared_read:
            raise ConnectorForbiddenError("Shared connector access is not allowed.")
        return connection
    if connection.owner_user_id != auth_user.user.id:
        raise ConnectorForbiddenError("User connector access denied.")
    return connection


def _ensure_scope_permission(scope: str, auth_user: AuthenticatedUser) -> None:
    _validate_owner_scope(scope)
    if scope == ConnectorOwnerScope.shared.value and not auth_user.is_admin:
        raise ConnectorForbiddenError("Shared connectors can only be managed by admins.")


async def start_google_drive_oauth(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    *,
    owner_scope: str,
    return_path: str = "/connectors",
) -> dict[str, str]:
    _ensure_google_drive_configured()
    owner_scope = _validate_owner_scope(owner_scope)
    _ensure_scope_permission(owner_scope, auth_user)
    verifier = generate_code_verifier()
    state = generate_state_token()
    session.add(
        ConnectorOAuthState(
            state=state,
            purpose=ConnectorOAuthPurpose.connect_drive.value,
            owner_scope=owner_scope,
            owner_user_id=auth_user.user.id if owner_scope == ConnectorOwnerScope.user.value else None,
            code_verifier=verifier,
            return_path=_safe_return_path(return_path),
            expires_at=future_utc(seconds=get_settings().oauth_state_ttl_seconds),
        )
    )
    await session.commit()

    params = httpx.QueryParams(
        {
            "client_id": get_settings().google_oauth_client_id,
            "redirect_uri": _app_callback_path("/api/connectors/google-drive/oauth/callback"),
            "response_type": "code",
            "scope": " ".join(CONNECTOR_SCOPES),
            "state": state,
            "code_challenge": create_code_challenge(verifier),
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return {"authorization_url": f"{GOOGLE_AUTH_URL}?{params}", "state": state}


async def complete_google_drive_oauth(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    *,
    state: str,
    code: str,
) -> ConnectorOAuthCallbackResponse:
    state_row = (
        await session.execute(
            select(ConnectorOAuthState).where(
                ConnectorOAuthState.state == state,
                ConnectorOAuthState.purpose == ConnectorOAuthPurpose.connect_drive.value,
            )
        )
    ).scalar_one_or_none()
    if state_row is None or state_row.expires_at < utcnow():
        raise ConnectorError("Connector OAuth state is invalid or expired.")
    if state_row.owner_scope == ConnectorOwnerScope.shared.value and not auth_user.is_admin:
        raise ConnectorForbiddenError("Shared connector callback requires an admin user.")
    if state_row.owner_scope == ConnectorOwnerScope.user.value and state_row.owner_user_id != auth_user.user.id:
        raise ConnectorForbiddenError("Connector callback user does not match the original owner.")

    token_data = await _exchange_google_code(
        code=code,
        code_verifier=state_row.code_verifier,
        redirect_uri=_app_callback_path("/api/connectors/google-drive/oauth/callback"),
    )
    userinfo = await _google_userinfo(str(token_data["access_token"]))
    owner_user_id = auth_user.user.id if state_row.owner_scope == ConnectorOwnerScope.user.value else None
    existing = (
        await session.execute(
            select(ConnectorConnection).where(
                ConnectorConnection.provider == ConnectorProvider.google_drive.value,
                ConnectorConnection.owner_scope == state_row.owner_scope,
                ConnectorConnection.account_subject == str(userinfo["sub"]),
                ConnectorConnection.owner_user_id == owner_user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = ConnectorConnection(
            provider=ConnectorProvider.google_drive.value,
            owner_scope=state_row.owner_scope,
            owner_user_id=owner_user_id,
            display_name=f"Google Drive ({userinfo.get('email') or 'account'})",
            account_email=str(userinfo.get("email") or ""),
            account_subject=str(userinfo["sub"]),
            status=ConnectorStatus.active.value,
            encrypted_access_token=encrypt_secret(str(token_data["access_token"])) or "",
            encrypted_refresh_token=encrypt_secret(str(token_data.get("refresh_token") or "")),
            token_expires_at=future_utc(seconds=int(token_data.get("expires_in", 3600))),
            granted_scopes=list(CONNECTOR_SCOPES),
            last_validated_at=utcnow(),
        )
        session.add(existing)
        await session.flush()
    else:
        existing.display_name = f"Google Drive ({userinfo.get('email') or existing.display_name})"
        existing.account_email = str(userinfo.get("email") or existing.account_email or "")
        existing.encrypted_access_token = encrypt_secret(str(token_data["access_token"])) or ""
        if token_data.get("refresh_token"):
            existing.encrypted_refresh_token = encrypt_secret(str(token_data["refresh_token"]))
        existing.token_expires_at = future_utc(seconds=int(token_data.get("expires_in", 3600)))
        existing.granted_scopes = list(CONNECTOR_SCOPES)
        existing.status = ConnectorStatus.active.value
        existing.last_validated_at = utcnow()
        await session.flush()
    await session.execute(delete(ConnectorOAuthState).where(ConnectorOAuthState.id == state_row.id))
    await session.commit()

    targets = list(
        (
            await session.execute(
                select(ConnectorSyncTarget).where(ConnectorSyncTarget.connection_id == existing.id).order_by(ConnectorSyncTarget.created_at.asc())
            )
        ).scalars().all()
    )
    return ConnectorOAuthCallbackResponse(
        redirect_to=state_row.return_path or "/connectors",
        connection=_connection_summary(existing, targets),
    )


async def get_connectors_readiness(
    session: AsyncSession,
    auth_user: AuthenticatedUser | None,
) -> ConnectorReadinessResponse:
    organization_connection = (
        await session.execute(
            select(ConnectorConnection)
            .where(ConnectorConnection.owner_scope == ConnectorOwnerScope.shared.value)
            .order_by(ConnectorConnection.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return ConnectorReadinessResponse(
        oauth_configured=_google_drive_configured(),
        organization_connection_exists=organization_connection is not None,
        organization_connection_status=organization_connection.status if organization_connection is not None else None,
        viewer_can_manage_org_connection=bool(auth_user and auth_user.is_admin),
    )


async def list_connections(session: AsyncSession, auth_user: AuthenticatedUser, *, scope: str) -> ConnectorListResponse:
    scope = _validate_owner_scope(scope)
    if scope == ConnectorOwnerScope.shared.value:
        stmt = select(ConnectorConnection).where(ConnectorConnection.owner_scope == ConnectorOwnerScope.shared.value)
    else:
        stmt = select(ConnectorConnection).where(
            ConnectorConnection.owner_scope == ConnectorOwnerScope.user.value,
            ConnectorConnection.owner_user_id == auth_user.user.id,
        )
    connections = list((await session.execute(stmt.order_by(ConnectorConnection.created_at.desc()))).scalars().all())
    targets = list(
        (
            await session.execute(
                select(ConnectorSyncTarget).where(ConnectorSyncTarget.connection_id.in_([connection.id for connection in connections]))
            )
        ).scalars().all()
    ) if connections else []
    targets_by_connection: dict[UUID, list[ConnectorSyncTarget]] = {}
    for target in targets:
        targets_by_connection.setdefault(target.connection_id, []).append(target)
    return ConnectorListResponse(items=[_connection_summary(connection, targets_by_connection.get(connection.id, [])) for connection in connections])


async def get_connection_detail(session: AsyncSession, auth_user: AuthenticatedUser, connection_id: UUID) -> ConnectorConnectionSummary:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    targets = list(
        (
            await session.execute(
                select(ConnectorSyncTarget).where(ConnectorSyncTarget.connection_id == connection.id).order_by(ConnectorSyncTarget.created_at.asc())
            )
        ).scalars().all()
    )
    return _connection_summary(connection, targets)


async def update_connection(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
    payload: ConnectorUpdateRequest,
) -> ConnectorConnectionSummary:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    _ensure_scope_permission(connection.owner_scope, auth_user) if connection.owner_scope == ConnectorOwnerScope.shared.value else None
    if payload.display_name is not None:
        connection.display_name = payload.display_name.strip() or connection.display_name
    if payload.status is not None:
        connection.status = payload.status
    await session.commit()
    return await get_connection_detail(session, auth_user, connection_id)


async def delete_connection(session: AsyncSession, auth_user: AuthenticatedUser, connection_id: UUID) -> None:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    if connection.owner_scope == ConnectorOwnerScope.shared.value:
        _ensure_scope_permission(connection.owner_scope, auth_user)
    await session.delete(connection)
    await session.commit()


async def browse_connection(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
    *,
    kind: str,
    parent_id: str | None = None,
    drive_id: str | None = None,
) -> ConnectorBrowseResponse:
    kind = _validate_browse_kind(kind)
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    if kind == ConnectorTargetType.shared_drive.value:
        data = await _google_json(session, connection, "/drives", params={"pageSize": 100})
        return ConnectorBrowseResponse(
            kind=kind,
            items=[
                ConnectorBrowseItem(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    kind=ConnectorTargetType.shared_drive.value,
                    drive_id=str(item["id"]),
                )
                for item in data.get("drives", [])
            ],
        )

    folder_parent = parent_id or "root"
    query = f"mimeType = '{GOOGLE_FOLDER_MIME}' and trashed = false and '{folder_parent}' in parents"
    params: dict[str, Any] = {
        "q": query,
        "pageSize": 100,
        "fields": "files(id,name,mimeType,parents,driveId)",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
        "orderBy": "name",
    }
    if drive_id:
        params["corpora"] = "drive"
        params["driveId"] = drive_id
    data = await _google_json(session, connection, "/files", params=params)
    return ConnectorBrowseResponse(
        kind=kind,
        parent_id=parent_id,
        drive_id=drive_id,
        items=[
            ConnectorBrowseItem(
                id=str(item["id"]),
                name=str(item["name"]),
                kind=ConnectorTargetType.folder.value,
                mime_type=item.get("mimeType"),
                drive_id=item.get("driveId"),
                parent_id=(item.get("parents") or [None])[0],
            )
            for item in data.get("files", [])
        ],
    )


def _normalize_sync_schedule(sync_mode: str, interval: int | None) -> tuple[str, int | None]:
    if sync_mode not in {ConnectorSyncMode.manual.value, ConnectorSyncMode.auto.value}:
        raise ConnectorError("Unsupported sync mode.")
    if sync_mode == ConnectorSyncMode.auto.value:
        interval = interval if interval in {15, 60, 360, 1440} else 60
        return sync_mode, interval
    return ConnectorSyncMode.manual.value, None


async def create_target(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
    payload: ConnectorTargetCreateRequest,
) -> ConnectorTargetSummary:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    if connection.owner_scope == ConnectorOwnerScope.shared.value:
        _ensure_scope_permission(connection.owner_scope, auth_user)
    target_type = _validate_target_type(payload.target_type)
    default_sync_mode, default_interval = _default_sync_schedule_for_scope(connection.owner_scope)
    sync_mode, interval = _normalize_sync_schedule(
        payload.sync_mode or default_sync_mode,
        payload.sync_interval_minutes if payload.sync_interval_minutes is not None else default_interval,
    )
    target = ConnectorSyncTarget(
        connection_id=connection.id,
        target_type=target_type,
        external_id=payload.external_id,
        name=payload.name,
        include_subfolders=payload.include_subfolders,
        sync_mode=sync_mode,
        sync_interval_minutes=interval,
        status=ConnectorTargetStatus.active.value,
        next_auto_sync_at=future_utc(seconds=interval * 60) if sync_mode == ConnectorSyncMode.auto.value and interval else None,
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)
    return _target_summary(target)


async def _get_target_or_raise(session: AsyncSession, target_id: UUID) -> ConnectorSyncTarget:
    target = await session.get(ConnectorSyncTarget, target_id)
    if target is None:
        raise ConnectorNotFoundError("Connector target not found.")
    return target


async def update_target(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
    target_id: UUID,
    payload: ConnectorTargetUpdateRequest,
) -> ConnectorTargetSummary:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    if connection.owner_scope == ConnectorOwnerScope.shared.value:
        _ensure_scope_permission(connection.owner_scope, auth_user)
    target = await _get_target_or_raise(session, target_id)
    if target.connection_id != connection.id:
        raise ConnectorNotFoundError("Connector target does not belong to the connection.")
    if payload.include_subfolders is not None:
        target.include_subfolders = payload.include_subfolders
    if payload.status is not None:
        target.status = payload.status
    if payload.sync_mode is not None or payload.sync_interval_minutes is not None:
        sync_mode, interval = _normalize_sync_schedule(payload.sync_mode or target.sync_mode, payload.sync_interval_minutes if payload.sync_interval_minutes is not None else target.sync_interval_minutes)
        target.sync_mode = sync_mode
        target.sync_interval_minutes = interval
        target.next_auto_sync_at = future_utc(seconds=interval * 60) if sync_mode == ConnectorSyncMode.auto.value and interval else None
    await session.commit()
    await session.refresh(target)
    return _target_summary(target)


async def delete_target(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
    target_id: UUID,
) -> None:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    if connection.owner_scope == ConnectorOwnerScope.shared.value:
        _ensure_scope_permission(connection.owner_scope, auth_user)
    target = await _get_target_or_raise(session, target_id)
    if target.connection_id != connection.id:
        raise ConnectorNotFoundError("Connector target does not belong to the connection.")
    await session.delete(target)
    await session.commit()


async def list_source_items(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
) -> list[ConnectorSourceItemSummary]:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    items = list(
        (
            await session.execute(
                select(ConnectorSourceItem)
                .where(ConnectorSourceItem.connection_id == connection.id)
                .order_by(ConnectorSourceItem.updated_at.desc())
                .limit(200)
            )
        ).scalars().all()
    )
    return [_source_item_summary(item) for item in items]


async def enqueue_connector_sync_job(
    session: AsyncSession,
    connection_id: UUID,
    target_id: UUID,
    *,
    sync_mode: str,
    priority: int,
) -> ConnectorSyncJob:
    existing = (
        await session.execute(
            select(ConnectorSyncJob).where(
                ConnectorSyncJob.target_id == target_id,
                ConnectorSyncJob.status.in_([JobStatus.queued.value, JobStatus.processing.value]),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    job = ConnectorSyncJob(
        connection_id=connection_id,
        target_id=target_id,
        sync_mode=sync_mode,
        status=JobStatus.queued.value,
        priority=priority,
        payload={},
    )
    session.add(job)
    await session.flush()
    return job


async def request_target_sync(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    connection_id: UUID,
    target_id: UUID,
) -> JobSummary:
    connection = await _get_connection_or_raise(session, connection_id, auth_user)
    if connection.owner_scope == ConnectorOwnerScope.shared.value:
        _ensure_scope_permission(connection.owner_scope, auth_user)
    target = await _get_target_or_raise(session, target_id)
    if target.connection_id != connection.id:
        raise ConnectorNotFoundError("Connector target does not belong to the connection.")
    job = await enqueue_connector_sync_job(
        session,
        connection.id,
        target.id,
        sync_mode=ConnectorSyncMode.manual.value,
        priority=80,
    )
    await session.commit()
    await session.refresh(job)
    return JobSummary(
        id=job.id,
        kind=ConnectorSyncJobKind.sync.value,
        title=f"Drive 동기화: {target.name}",
        status=job.status,
        priority=job.priority,
        attempt_count=job.attempt_count,
        error_message=job.error_message,
        requested_at=job.requested_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


async def enqueue_due_sync_jobs(session: AsyncSession, *, limit: int = 10) -> int:
    due_targets = list(
        (
            await session.execute(
                select(ConnectorSyncTarget)
                .where(
                    ConnectorSyncTarget.sync_mode == ConnectorSyncMode.auto.value,
                    ConnectorSyncTarget.status == ConnectorTargetStatus.active.value,
                    ConnectorSyncTarget.next_auto_sync_at.is_not(None),
                    ConnectorSyncTarget.next_auto_sync_at <= utcnow(),
                )
                .order_by(ConnectorSyncTarget.next_auto_sync_at.asc())
                .limit(limit)
            )
        ).scalars().all()
    )
    created = 0
    for target in due_targets:
        existing = (
            await session.execute(
                select(ConnectorSyncJob).where(
                    ConnectorSyncJob.target_id == target.id,
                    ConnectorSyncJob.status.in_([JobStatus.queued.value, JobStatus.processing.value]),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        await enqueue_connector_sync_job(
            session,
            target.connection_id,
            target.id,
            sync_mode=ConnectorSyncMode.auto.value,
            priority=95,
        )
        created += 1
    if created:
        await session.commit()
    return created


async def acquire_next_connector_sync_job(session: AsyncSession) -> ConnectorSyncJob | None:
    job = (
        await session.execute(
            select(ConnectorSyncJob)
            .where(
                ConnectorSyncJob.status.in_([JobStatus.queued.value, JobStatus.failed.value]),
            )
            .where(ConnectorSyncJob.attempt_count < get_settings().worker_max_attempts)
            .order_by(ConnectorSyncJob.priority.asc(), ConnectorSyncJob.requested_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if job is None:
        return None
    job.status = JobStatus.processing.value
    job.started_at = utcnow()
    job.finished_at = None
    job.last_heartbeat_at = utcnow()
    job.attempt_count += 1
    job.error_message = None
    await session.flush()
    return job


async def mark_connector_job_failed(session: AsyncSession, job_id: UUID, message: str) -> None:
    job = await session.get(ConnectorSyncJob, job_id)
    if job is None:
        return
    job.status = JobStatus.failed.value
    job.error_message = message[:4000]
    job.finished_at = utcnow()
    job.last_heartbeat_at = utcnow()
    await session.flush()


async def mark_connector_job_completed(session: AsyncSession, job_id: UUID, payload: dict[str, Any]) -> None:
    job = await session.get(ConnectorSyncJob, job_id)
    if job is None:
        return
    job.status = JobStatus.completed.value
    job.error_message = None
    job.finished_at = utcnow()
    job.last_heartbeat_at = utcnow()
    job.payload = payload
    await session.flush()


def _markdown_table(rows: list[list[Any]]) -> str:
    if not rows:
        return ""
    normalized = [["" if cell is None else str(cell).replace("\n", " ").strip() for cell in row] for row in rows]
    header = normalized[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in normalized[1:]:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def _extract_xlsx(data: bytes) -> ExtractedContent:
    workbook = load_workbook(io.BytesIO(data), data_only=True)
    parts: list[str] = []
    for sheet in workbook.worksheets:
        parts.append(f"## {sheet.title}")
        rows = [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]
        if rows:
            parts.append(_markdown_table(rows))
        else:
            parts.append("_빈 시트_")
    return ExtractedContent(content_type="markdown", content="\n\n".join(parts).strip(), doc_type="data")


def _extract_docx(data: bytes) -> ExtractedContent:
    document = DocxDocument(io.BytesIO(data))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return ExtractedContent(content_type="text", content="\n\n".join(paragraphs).strip(), doc_type="knowledge")


def _extract_pptx(data: bytes) -> ExtractedContent:
    presentation = Presentation(io.BytesIO(data))
    slides: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        lines = [f"## Slide {index}"]
        for shape in slide.shapes:
            if hasattr(shape, "text") and str(shape.text).strip():
                lines.append(str(shape.text).strip())
        slides.append("\n\n".join(lines))
    return ExtractedContent(content_type="markdown", content="\n\n".join(slides).strip(), doc_type="knowledge")


def _extract_pdf(data: bytes) -> ExtractedContent:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return ExtractedContent(content_type="text", content=normalize_whitespace("\n\n".join(pages)), doc_type="knowledge")


def _extract_image(data: bytes) -> ExtractedContent:
    image = Image.open(io.BytesIO(data))
    text = pytesseract.image_to_string(image)
    return ExtractedContent(content_type="text", content=normalize_whitespace(text), doc_type="knowledge")


def _extract_csv(data: bytes) -> ExtractedContent:
    decoded = data.decode("utf-8-sig", errors="ignore")
    rows = list(csv.reader(io.StringIO(decoded)))
    return ExtractedContent(content_type="markdown", content=_markdown_table(rows), doc_type="data")


def extract_file_content(file_meta: dict[str, Any], data: bytes) -> ExtractedContent:
    mime_type = str(file_meta.get("mimeType") or "")
    name = str(file_meta.get("name") or "document")
    lower_name = name.lower()

    if mime_type == "text/html" or lower_name.endswith((".html", ".htm")):
        return ExtractedContent(content_type="html", content=data.decode("utf-8", errors="ignore"), doc_type="knowledge")
    if mime_type in {"text/plain", "text/markdown"} or lower_name.endswith((".txt", ".md", ".markdown")):
        doc_type = "data" if lower_name.endswith(".csv") else "knowledge"
        return ExtractedContent(content_type="markdown" if lower_name.endswith((".md", ".markdown")) else "text", content=data.decode("utf-8-sig", errors="ignore"), doc_type=doc_type)
    if mime_type == "text/csv" or lower_name.endswith(".csv"):
        return _extract_csv(data)
    if mime_type == "application/pdf" or lower_name.endswith(".pdf"):
        return _extract_pdf(data)
    if lower_name.endswith(".docx"):
        return _extract_docx(data)
    if lower_name.endswith(".xlsx"):
        return _extract_xlsx(data)
    if lower_name.endswith(".pptx"):
        return _extract_pptx(data)
    if mime_type.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")):
        return _extract_image(data)
    raise ConnectorError(f"Unsupported file type: {mime_type or lower_name}")


async def _download_google_file(session: AsyncSession, connection: ConnectorConnection, file_meta: dict[str, Any]) -> ExtractedContent:
    file_id = str(file_meta["id"])
    mime_type = str(file_meta.get("mimeType") or "")
    if mime_type == GOOGLE_DOC_MIME:
        data = await _google_bytes(session, connection, f"/files/{file_id}/export", params={"mimeType": "text/html"})
        return ExtractedContent(content_type="html", content=data.decode("utf-8", errors="ignore"), doc_type="knowledge")
    if mime_type == GOOGLE_SHEET_MIME:
        data = await _google_bytes(session, connection, f"/files/{file_id}/export", params={"mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})
        return _extract_xlsx(data)
    if mime_type == GOOGLE_SLIDE_MIME:
        data = await _google_bytes(session, connection, f"/files/{file_id}/export", params={"mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation"})
        return _extract_pptx(data)
    if mime_type == GOOGLE_DRAWING_MIME:
        data = await _google_bytes(session, connection, f"/files/{file_id}/export", params={"mimeType": "application/pdf"})
        return _extract_pdf(data)
    data = await _google_bytes(session, connection, f"/files/{file_id}", params={"alt": "media", "supportsAllDrives": "true"})
    return extract_file_content(file_meta, data)


async def _list_drive_files_paginated(
    session: AsyncSession,
    connection: ConnectorConnection,
    *,
    q: str,
    drive_id: str | None = None,
) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "q": q,
            "pageSize": 1000,
            "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,version,md5Checksum,webViewLink,fileExtension,parents,trashed,driveId)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if drive_id:
            params["corpora"] = "drive"
            params["driveId"] = drive_id
        if page_token:
            params["pageToken"] = page_token
        data = await _google_json(session, connection, "/files", params=params)
        files.extend(list(data.get("files", [])))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return files


async def _discover_target_files(session: AsyncSession, connection: ConnectorConnection, target: ConnectorSyncTarget) -> list[dict[str, Any]]:
    if target.target_type == ConnectorTargetType.shared_drive.value:
        return [
            item
            for item in await _list_drive_files_paginated(
                session,
                connection,
                q="trashed = false",
                drive_id=target.external_id,
            )
            if item.get("mimeType") != GOOGLE_FOLDER_MIME
        ]

    queue: deque[str] = deque([target.external_id])
    seen_folders: set[str] = set()
    files: list[dict[str, Any]] = []
    while queue:
        folder_id = queue.popleft()
        if folder_id in seen_folders:
            continue
        seen_folders.add(folder_id)
        children = await _list_drive_files_paginated(
            session,
            connection,
            q=f"trashed = false and '{folder_id}' in parents",
        )
        for child in children:
            if child.get("mimeType") == GOOGLE_FOLDER_MIME:
                if target.include_subfolders:
                    queue.append(str(child["id"]))
                continue
            files.append(child)
    return files


async def _upsert_source_item(
    session: AsyncSession,
    *,
    connection_id: UUID,
    target_id: UUID,
    file_meta: dict[str, Any],
    document_id: UUID | None,
    status: str,
    unsupported_reason: str | None = None,
    error_message: str | None = None,
) -> ConnectorSourceItem:
    item = (
        await session.execute(
            select(ConnectorSourceItem).where(
                ConnectorSourceItem.connection_id == connection_id,
                ConnectorSourceItem.target_id == target_id,
                ConnectorSourceItem.external_file_id == str(file_meta["id"]),
            )
        )
    ).scalar_one_or_none()
    if item is None:
        item = ConnectorSourceItem(
            connection_id=connection_id,
            target_id=target_id,
            external_file_id=str(file_meta["id"]),
            mime_type=file_meta.get("mimeType"),
            name=str(file_meta.get("name") or file_meta["id"]),
            source_url=file_meta.get("webViewLink"),
            source_revision_id=_revision_token(file_meta),
            internal_document_id=document_id,
            item_status=status,
            unsupported_reason=unsupported_reason,
            error_message=error_message,
            last_seen_at=utcnow(),
            last_synced_at=utcnow(),
        )
        session.add(item)
    else:
        item.mime_type = file_meta.get("mimeType")
        item.name = str(file_meta.get("name") or item.name)
        item.source_url = file_meta.get("webViewLink")
        item.source_revision_id = _revision_token(file_meta)
        item.internal_document_id = document_id
        item.item_status = status
        item.unsupported_reason = unsupported_reason
        item.error_message = error_message
        item.last_seen_at = utcnow()
        item.last_synced_at = utcnow()
    await session.flush()
    return item


async def _archive_document_if_unreferenced(session: AsyncSession, document_id: UUID | None) -> None:
    if document_id is None:
        return
    remaining = int(
        (
            await session.execute(
                select(func.count(ConnectorSourceItem.id)).where(
                    ConnectorSourceItem.internal_document_id == document_id,
                    ConnectorSourceItem.item_status.in_(
                        [
                            ConnectorSourceItemStatus.imported.value,
                            ConnectorSourceItemStatus.unchanged.value,
                            ConnectorSourceItemStatus.failed.value,
                            ConnectorSourceItemStatus.unsupported.value,
                        ]
                    ),
                )
            )
        ).scalar_one()
    )
    if remaining > 0:
        return
    document = await session.get(Document, document_id)
    if document is not None:
        document.status = "archived"
        await session.flush()


async def process_connector_sync_job(session_factory: async_sessionmaker[AsyncSession], job_id: UUID) -> None:
    async with session_factory() as session:
        job = await session.get(ConnectorSyncJob, job_id)
        if job is None:
            return
        connection = await session.get(ConnectorConnection, job.connection_id)
        target = await session.get(ConnectorSyncTarget, job.target_id)
        if connection is None or target is None:
            raise ConnectorError("Connector sync job references missing connection/target.")
        target.last_sync_started_at = utcnow()
        await session.commit()

        discovered_files = await _discover_target_files(session, connection, target)
        seen_ids = {str(item["id"]) for item in discovered_files}
        counts = {"imported": 0, "unchanged": 0, "unsupported": 0, "failed": 0, "deleted": 0}

        for file_meta in discovered_files:
            try:
                extracted = await _download_google_file(session, connection, file_meta)
                if not extracted.content.strip():
                    raise ConnectorError("Extracted content is empty.")
                payload = IngestDocumentRequest(
                    source_system="google-drive",
                    source_external_id=str(file_meta["id"]),
                    source_revision_id=_revision_token(file_meta),
                    source_url=file_meta.get("webViewLink"),
                    slug=_stable_document_slug(str(file_meta.get("name") or file_meta["id"]), str(file_meta["id"])),
                    title=str(file_meta.get("name") or file_meta["id"]),
                    content_type=extracted.content_type,  # type: ignore[arg-type]
                    content=extracted.content,
                    doc_type=extracted.doc_type,
                    language_code="ko",
                    status="published",
                    metadata={
                        "provider": "google-drive",
                        "google_mime_type": file_meta.get("mimeType"),
                        "connector_connection_id": str(connection.id),
                        "connector_target_id": str(target.id),
                    },
                    priority=110,
                )
                result = await ingest_document(session, payload)
                status = ConnectorSourceItemStatus.unchanged.value if result.unchanged else ConnectorSourceItemStatus.imported.value
                counts["unchanged" if result.unchanged else "imported"] += 1
                await _upsert_source_item(
                    session,
                    connection_id=connection.id,
                    target_id=target.id,
                    file_meta=file_meta,
                    document_id=result.document.id,
                    status=status,
                )
            except ConnectorError as exc:
                counts["unsupported"] += 1
                await _upsert_source_item(
                    session,
                    connection_id=connection.id,
                    target_id=target.id,
                    file_meta=file_meta,
                    document_id=None,
                    status=ConnectorSourceItemStatus.unsupported.value,
                    unsupported_reason=str(exc),
                )
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                counts["failed"] += 1
                await _upsert_source_item(
                    session,
                    connection_id=connection.id,
                    target_id=target.id,
                    file_meta=file_meta,
                    document_id=None,
                    status=ConnectorSourceItemStatus.failed.value,
                    error_message=str(exc),
                )
                await session.commit()

        existing_items = list(
            (
                await session.execute(select(ConnectorSourceItem).where(ConnectorSourceItem.target_id == target.id))
            ).scalars().all()
        )
        for item in existing_items:
            if item.external_file_id in seen_ids:
                continue
            item.item_status = ConnectorSourceItemStatus.deleted.value
            item.last_synced_at = utcnow()
            counts["deleted"] += 1
            await _archive_document_if_unreferenced(session, item.internal_document_id)

        target.last_sync_completed_at = utcnow()
        target.last_sync_summary = counts
        if target.sync_mode == ConnectorSyncMode.auto.value and target.sync_interval_minutes:
            target.next_auto_sync_at = future_utc(seconds=target.sync_interval_minutes * 60)
        else:
            target.next_auto_sync_at = None
        await mark_connector_job_completed(session, job.id, counts)
        await session.commit()
