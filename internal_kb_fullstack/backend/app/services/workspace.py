from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import future_utc, generate_state_token, session_token_hash, utcnow
from app.db.models import (
    ConnectorConnection,
    ConnectorOwnerScope,
    ConnectorProvider,
    ConnectorResource,
    ConnectorResourceStatus,
    ConnectorStatus,
    ConnectorSyncJob,
    GlossaryValidationRun,
    JobStatus,
    KnowledgeConcept,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
    WorkspaceMembershipRole,
)
from app.schemas.documents import DocumentListItem
from app.schemas.glossary import GlossaryConceptSummary
from app.schemas.jobs import JobSummary
from app.schemas.workspace import (
    WorkspaceContextResponse,
    WorkspaceInvitationAcceptResponse,
    WorkspaceInvitationCreateRequest,
    WorkspaceInvitationCreateResponse,
    WorkspaceInvitationPreviewResponse,
    WorkspaceInvitationSummary,
    WorkspaceMemberSummary,
    WorkspaceOverviewResponse,
    WorkspaceSourceHealthSummary,
    WorkspaceSummary,
)
from app.services.auth import AuthenticatedUser, current_workspace_summary, set_current_workspace_for_session
from app.services.catalog import list_documents
from app.services.glossary import _validation_run_summary, list_glossary_concepts
from app.services.trust import build_document_trust

WORKSPACE_ADMIN_ROLES = {WorkspaceMembershipRole.owner.value, WorkspaceMembershipRole.admin.value}


class WorkspaceError(RuntimeError):
    pass


class WorkspaceForbiddenError(WorkspaceError):
    pass


class WorkspaceNotFoundError(WorkspaceError):
    pass


async def get_default_workspace(session: AsyncSession) -> Workspace | None:
    workspace = (
        await session.execute(
            select(Workspace).where(Workspace.is_default.is_(True)).order_by(Workspace.created_at.asc()).limit(1)
        )
    ).scalar_one_or_none()
    if workspace is not None:
        return workspace
    return (
        await session.execute(select(Workspace).order_by(Workspace.created_at.asc()).limit(1))
    ).scalar_one_or_none()


async def resolve_read_workspace_id(
    session: AsyncSession,
    auth_user: AuthenticatedUser | None,
) -> UUID | None:
    if auth_user is not None:
        if auth_user.current_workspace_id is not None:
            return auth_user.current_workspace_id
        default_workspace = await get_default_workspace(session)
        return default_workspace.id if default_workspace is not None else None
    default_workspace = await get_default_workspace(session)
    return default_workspace.id if default_workspace is not None else None


def _require_workspace(auth_user: AuthenticatedUser) -> UUID:
    if auth_user.current_workspace_id is None:
        raise WorkspaceForbiddenError("Workspace context is required.")
    return auth_user.current_workspace_id


def _require_workspace_admin(auth_user: AuthenticatedUser) -> UUID:
    workspace_id = _require_workspace(auth_user)
    if not auth_user.can_manage_workspace_connectors:
        raise WorkspaceForbiddenError("Workspace admin permission required.")
    return workspace_id


def _normalize_invited_email(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or "@" not in normalized:
        raise WorkspaceError("A valid invited_email is required.")
    return normalized


def _validate_invitation_role(role: str, auth_user: AuthenticatedUser) -> str:
    normalized = role.strip().lower()
    if normalized not in {
        WorkspaceMembershipRole.owner.value,
        WorkspaceMembershipRole.admin.value,
        WorkspaceMembershipRole.member.value,
    }:
        raise WorkspaceError("Unsupported workspace role.")
    if normalized == WorkspaceMembershipRole.owner.value and auth_user.current_workspace_role != WorkspaceMembershipRole.owner.value:
        raise WorkspaceForbiddenError("Only workspace owners can invite another owner.")
    return normalized


def _invitation_summary(invitation: WorkspaceInvitation) -> WorkspaceInvitationSummary:
    return WorkspaceInvitationSummary(
        id=invitation.id,
        workspace_id=invitation.workspace_id,
        invited_email=invitation.invited_email,
        role=invitation.role,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
    )


async def preview_workspace_invitation(
    session: AsyncSession,
    *,
    invitation_token: str,
) -> WorkspaceInvitationPreviewResponse:
    invitation = (
        await session.execute(
            select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == session_token_hash(invitation_token))
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise WorkspaceNotFoundError("Workspace invitation not found.")

    workspace = await session.get(Workspace, invitation.workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError("Workspace not found.")

    existing_user = (
        await session.execute(select(User).where(User.email == invitation.invited_email.strip().lower()))
    ).scalar_one_or_none()

    return WorkspaceInvitationPreviewResponse(
        invited_email=invitation.invited_email,
        workspace=WorkspaceSummary(
            id=workspace.id,
            slug=workspace.slug,
            name=workspace.name,
            is_default=workspace.is_default,
        ),
        role=invitation.role,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        is_expired=invitation.expires_at < utcnow(),
        local_password_exists=bool(existing_user and existing_user.password_hash),
    )


async def get_current_workspace(auth_user: AuthenticatedUser) -> WorkspaceContextResponse:
    return WorkspaceContextResponse(
        workspace=current_workspace_summary(auth_user),
        role=auth_user.current_workspace_role,
        can_manage_connectors=auth_user.can_manage_workspace_connectors,
    )


def _document_list_item(row: dict[str, object]) -> DocumentListItem:
    return DocumentListItem(
        **row,
        trust=build_document_trust(
            source_system=str(row.get("source_system") or ""),
            source_url=row.get("source_url") if isinstance(row.get("source_url"), str) else None,
            last_synced_at=row.get("last_ingested_at"),  # type: ignore[arg-type]
            doc_type=row.get("doc_type") if isinstance(row.get("doc_type"), str) else None,
        ),
    )


async def get_workspace_overview(
    session: AsyncSession,
    auth_user: AuthenticatedUser | None,
) -> WorkspaceOverviewResponse:
    if auth_user is not None and auth_user.current_workspace_id is None:
        return WorkspaceOverviewResponse(
            authenticated=True,
            workspace=None,
            viewer_role=None,
            can_manage_connectors=False,
            featured_docs=[],
            featured_concepts=[],
            setup_state="workspace_access_required",
            next_actions=[
                "워크스페이스 관리자에게 초대 링크를 요청하세요.",
                "초대를 수락하면 검색, 문서, 핵심 개념 화면이 워크스페이스 기준으로 활성화됩니다.",
            ],
            recent_sync_issues=[],
            verification_counts={},
        )

    read_workspace_id = await resolve_read_workspace_id(session, auth_user)
    rows, _total = await list_documents(session, workspace_id=read_workspace_id, limit=6)
    featured_docs = [_document_list_item(row) for row in rows]
    featured_concepts = (
        await list_glossary_concepts(
            session,
            workspace_id=read_workspace_id,
            status_filter="approved",
            limit=6,
        )
    ).items
    latest_validation_run = None
    review_required_count = 0
    verification_counts: dict[str, int] = {}

    if auth_user is None:
        return WorkspaceOverviewResponse(
            authenticated=False,
            featured_docs=featured_docs,
            featured_concepts=featured_concepts,
            verification_counts=verification_counts,
            setup_state="anonymous",
            next_actions=[
                "로그인하고 워크스페이스 지식 레이어를 시작하세요.",
                "구성원은 연결 구조를 몰라도 검색과 문서 탐색으로 바로 답을 찾을 수 있습니다.",
            ],
        )

    workspace_id = auth_user.current_workspace_id
    workspace_connections = list(
        (
            await session.execute(
                select(ConnectorConnection).where(
                    ConnectorConnection.workspace_id == workspace_id,
                    ConnectorConnection.owner_scope == ConnectorOwnerScope.workspace.value,
                )
            )
        ).scalars().all()
    )
    workspace_connection_ids = [connection.id for connection in workspace_connections]
    resources = list(
        (
            await session.execute(
                select(ConnectorResource).where(ConnectorResource.connection_id.in_(workspace_connection_ids))
            )
        ).scalars().all()
    ) if workspace_connection_ids else []
    recent_sync_issues = list(
        (
            await session.execute(
                select(ConnectorSyncJob)
                .where(
                    ConnectorSyncJob.status == JobStatus.failed.value,
                    ConnectorSyncJob.connection_id.in_(workspace_connection_ids),
                )
                .order_by(ConnectorSyncJob.requested_at.desc())
                .limit(5)
            )
        ).scalars().all()
    ) if workspace_connection_ids else []
    resources_by_id = {resource.id: resource for resource in resources}
    latest_validation_run_row = (
        await session.execute(
            select(GlossaryValidationRun)
            .where(GlossaryValidationRun.workspace_id == workspace_id)
            .order_by(GlossaryValidationRun.requested_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_validation_run_row is not None:
        latest_validation_run = _validation_run_summary(latest_validation_run_row)
    review_required_count = int(
        (
            await session.execute(
                select(func.count(KnowledgeConcept.id)).where(
                    KnowledgeConcept.workspace_id == workspace_id,
                    KnowledgeConcept.review_required.is_(True),
                )
            )
        ).scalar_one()
    )
    verification_rows = (
        await session.execute(
            select(KnowledgeConcept.verification_state, func.count(KnowledgeConcept.id))
            .where(KnowledgeConcept.workspace_id == workspace_id)
            .group_by(KnowledgeConcept.verification_state)
        )
    ).all()
    verification_counts = {str(state): int(count) for state, count in verification_rows}

    healthy_source_count = sum(
        1
        for resource in resources
        if resource.status == ConnectorResourceStatus.active.value and int((resource.last_sync_summary or {}).get("failed", 0)) == 0
    )
    needs_attention_count = sum(
        1
        for resource in resources
        if resource.status != ConnectorResourceStatus.active.value or int((resource.last_sync_summary or {}).get("failed", 0)) > 0
    ) + sum(1 for connection in workspace_connections if connection.status != ConnectorStatus.active.value)
    providers_needing_attention = sorted(
        {
            connection.provider
            for connection in workspace_connections
            if connection.status != ConnectorStatus.active.value
        }
    )

    if not workspace_connections:
        setup_state = "setup_needed"
        next_actions = [
            "Google Drive, GitHub, Notion 중 하나를 연결해 워크스페이스 지식 레이어를 시작하세요.",
            "낮은 수준의 연결 리소스 대신 팀용 템플릿부터 선택하세요.",
        ]
    elif needs_attention_count > 0:
        setup_state = "attention_required"
        next_actions = [
            "주의가 필요한 데이터 소스를 다시 연결하세요.",
            "최근 동기화 실패를 확인하고 영향을 받은 소스를 다시 실행하세요.",
        ]
    else:
        setup_state = "ready"
        next_actions = [
            "검색과 문서 탐색을 워크스페이스 기본 진입점으로 사용하세요.",
            "지식 검수에서 변경된 용어 정의만 검토해도 충분합니다.",
        ]

    sync_issue_summaries = [
        JobSummary.model_validate(job).model_copy(
            update={
                "kind": job.kind,
                "title": (
                    f"리소스 동기화: {resources_by_id[job.resource_id].name}"
                    if job.resource_id is not None and job.resource_id in resources_by_id
                    else "리소스 동기화 실패"
                ),
                "resource_id": job.resource_id,
                "connection_id": job.connection_id,
            }
        )
        for job in recent_sync_issues
    ]

    return WorkspaceOverviewResponse(
        authenticated=True,
        workspace=current_workspace_summary(auth_user),
        viewer_role=auth_user.current_workspace_role,
        can_manage_connectors=auth_user.can_manage_workspace_connectors,
        setup_state=setup_state,
        next_actions=next_actions,
        source_health=WorkspaceSourceHealthSummary(
            workspace_connection_count=len(workspace_connections),
            healthy_source_count=healthy_source_count,
            needs_attention_count=needs_attention_count,
            providers_needing_attention=providers_needing_attention,
        ),
        featured_docs=featured_docs,
        featured_concepts=featured_concepts,
        recent_sync_issues=sync_issue_summaries,
        latest_validation_run=latest_validation_run,
        review_required_count=review_required_count,
        verification_counts=verification_counts,
    )


async def list_workspace_members(session: AsyncSession, auth_user: AuthenticatedUser) -> list[WorkspaceMemberSummary]:
    workspace_id = _require_workspace(auth_user)
    rows = (
        await session.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.created_at.asc(), User.email.asc())
        )
    ).all()
    return [
        WorkspaceMemberSummary(
            user_id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=membership.role,
            created_at=membership.created_at,
        )
        for membership, user in rows
    ]


async def list_workspace_invitations(session: AsyncSession, auth_user: AuthenticatedUser) -> list[WorkspaceInvitationSummary]:
    workspace_id = _require_workspace_admin(auth_user)
    invitations = list(
        (
            await session.execute(
                select(WorkspaceInvitation)
                .where(WorkspaceInvitation.workspace_id == workspace_id)
                .order_by(WorkspaceInvitation.created_at.desc())
                .limit(100)
            )
        ).scalars().all()
    )
    return [_invitation_summary(invitation) for invitation in invitations]


async def create_workspace_invitation(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    payload: WorkspaceInvitationCreateRequest,
) -> WorkspaceInvitationCreateResponse:
    workspace_id = _require_workspace_admin(auth_user)
    invited_email = _normalize_invited_email(payload.invited_email)
    role = _validate_invitation_role(payload.role, auth_user)
    raw_token = generate_state_token()
    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        invited_email=invited_email,
        role=role,
        token_hash=session_token_hash(raw_token),
        expires_at=future_utc(seconds=get_settings().workspace_invitation_ttl_seconds),
        created_by_user_id=auth_user.user.id,
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    invite_url = f"{get_settings().app_public_url.rstrip('/')}/invite/{raw_token}"
    return WorkspaceInvitationCreateResponse(
        invitation=_invitation_summary(invitation),
        invite_url=invite_url,
    )


async def accept_workspace_invitation(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    *,
    invitation_token: str,
    session_token: str | None,
) -> WorkspaceInvitationAcceptResponse:
    invitation = (
        await session.execute(
            select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == session_token_hash(invitation_token))
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise WorkspaceNotFoundError("Workspace invitation not found.")
    if invitation.expires_at < utcnow():
        raise WorkspaceError("Workspace invitation has expired.")

    invited_email = invitation.invited_email.strip().lower()
    current_email = auth_user.user.email.strip().lower()
    if invited_email != current_email:
        raise WorkspaceForbiddenError("Workspace invitation email does not match the signed-in user.")

    workspace = await session.get(Workspace, invitation.workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError("Workspace not found.")

    membership = (
        await session.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == invitation.workspace_id,
                WorkspaceMembership.user_id == auth_user.user.id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        membership = WorkspaceMembership(
            workspace_id=invitation.workspace_id,
            user_id=auth_user.user.id,
            role=invitation.role,
        )
        session.add(membership)
        await session.flush()

    if invitation.accepted_at is None:
        invitation.accepted_at = utcnow()
        invitation.accepted_by_user_id = auth_user.user.id

    await set_current_workspace_for_session(session, session_token, invitation.workspace_id)
    await session.commit()
    return WorkspaceInvitationAcceptResponse(
        workspace=WorkspaceSummary(
            id=workspace.id,
            slug=workspace.slug,
            name=workspace.name,
            is_default=workspace.is_default,
        ),
        role=membership.role,
    )
