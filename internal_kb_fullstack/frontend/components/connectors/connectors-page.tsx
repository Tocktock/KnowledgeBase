'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  BookMarked,
  CheckCircle2,
  Copy,
  ExternalLink,
  FolderOpen,
  HardDrive,
  KeyRound,
  Link2,
  LoaderCircle,
  Lock,
  RefreshCcw,
  Search,
  ShieldCheck,
  Trash2,
  UserRound,
  UserPlus,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import type { ReactNode } from 'react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type {
  AuthMeResponse,
  ConnectorBrowseItem,
  ConnectorBrowseResponse,
  ConnectorConnectionSummary,
  ConnectorListResponse,
  ConnectorProviderReadiness,
  ConnectorReadinessResponse,
  ConnectorResourceCreateRequest,
  ConnectorResourceSummary,
  ConnectorSourceItemSummary,
  JobSummary,
  PasswordResetLinkCreateResponse,
  WorkspaceInvitationCreateResponse,
  WorkspaceInvitationSummary,
  WorkspaceMemberSummary,
} from '@/lib/types'
import {
  formatConnectorItemStatusLabel,
  formatConnectorProviderLabel,
  formatConnectorResourceKindLabel,
  formatConnectorStatusLabel,
  formatConnectorSyncModeLabel,
  formatDate,
  formatStatusLabel,
} from '@/lib/utils'

type Scope = 'workspace' | 'personal'
type SyncMode = 'manual' | 'auto'
type ProviderKey = 'google_drive' | 'notion'
type ProviderPath = 'google-drive' | 'notion'
type GoogleResourceKind = 'folder' | 'shared_drive'
type NotionResourceKind = 'page' | 'database'
type ResourceKind = GoogleResourceKind | NotionResourceKind
type ResourceRecord = {
  connection: ConnectorConnectionSummary
  resource: ConnectorResourceSummary
}

type ProviderTemplate = {
  id: string
  resourceKind: ResourceKind
  organizationLabel: string
  personalLabel: string
  description: string
}

type ProviderDefinition = {
  key: ProviderKey
  path: ProviderPath
  label: string
  description: string
  organizationDescription: string
  personalDescription: string
  icon: LucideIcon
  templates: ProviderTemplate[]
}

const providerDefinitions: ProviderDefinition[] = [
  {
    key: 'google_drive',
    path: 'google-drive',
    label: 'Google Drive',
    description: '팀 문서와 공유 드라이브를 기존 문서 저장소로 가져옵니다.',
    organizationDescription: '조직 관리자가 공유 드라이브나 팀 폴더를 한 번 연결하면 전사 문서 검색에 바로 반영됩니다.',
    personalDescription: '내 Drive 폴더를 필요할 때만 연결해 개인 메모나 참고 문서를 가져옵니다.',
    icon: HardDrive,
    templates: [
      {
        id: 'shared_drive',
        resourceKind: 'shared_drive',
        organizationLabel: '공유 드라이브 연결',
        personalLabel: '내 공유 드라이브 연결',
        description: '부서 전체 문서가 담긴 공유 드라이브를 연결합니다.',
      },
      {
        id: 'folder',
        resourceKind: 'folder',
        organizationLabel: '팀 폴더 연결',
        personalLabel: '내 폴더 연결',
        description: '특정 폴더와 하위 폴더 문서를 함께 가져옵니다.',
      },
    ],
  },
  {
    key: 'notion',
    path: 'notion',
    label: 'Notion',
    description: '팀 위키 페이지와 데이터베이스를 검색형 선택기로 연결합니다.',
    organizationDescription: '조직 관리자가 팀 위키 페이지나 데이터베이스를 연결하면 공용 문서 저장소로 동기화됩니다.',
    personalDescription: '내 Notion 페이지나 데이터베이스를 필요할 때만 연결합니다.',
    icon: BookMarked,
    templates: [
      {
        id: 'page',
        resourceKind: 'page',
        organizationLabel: '팀 위키 페이지 연결',
        personalLabel: '내 페이지 연결',
        description: '선택한 페이지 한 개를 문서 저장소로 가져옵니다.',
      },
      {
        id: 'database',
        resourceKind: 'database',
        organizationLabel: '팀 데이터베이스 연결',
        personalLabel: '내 데이터베이스 연결',
        description: '데이터베이스의 하위 페이지 전체를 함께 가져옵니다.',
      },
    ],
  },
]

const intervalOptions = [
  { value: 15, label: '15분마다' },
  { value: 60, label: '1시간마다' },
  { value: 360, label: '6시간마다' },
  { value: 1440, label: '24시간마다' },
]

const selectClassName =
  'h-11 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm text-neutral-900 outline-none ring-0 focus:border-blue-500 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100'

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || '요청에 실패했습니다.')
  }
  if (response.status === 204) {
    return null as T
  }
  return (await response.json()) as T
}

function getErrorMessage(searchParams: URLSearchParams) {
  const authError = searchParams.get('auth_error')
  const connectorError = searchParams.get('connector_error')
  if (authError === 'login_failed') return 'Google 로그인 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.'
  if (authError === 'login_unavailable') return '관리자가 연결 기능을 아직 준비하지 않았습니다.'
  if (connectorError === 'session_missing') return '다시 로그인한 뒤 연결을 시작해 주세요.'
  if (connectorError === 'org_admin_required') return '조직 데이터 소스는 관리자만 연결할 수 있습니다.'
  if (connectorError === 'start_failed') return '연결 시작에 실패했습니다.'
  if (connectorError === 'callback_failed') return '연결 확인 처리에 실패했습니다.'
  return null
}

function providerDefinition(provider: string) {
  return providerDefinitions.find((item) => item.key === provider) ?? providerDefinitions[0]
}

function templateLabel(template: ProviderTemplate, scope: Scope) {
  return scope === 'workspace' ? template.organizationLabel : template.personalLabel
}

function connectHref(provider: ProviderDefinition, scope: Scope) {
  return `/api/connectors/${provider.path}/oauth/start?scope=${scope}&return_to=${encodeURIComponent('/connectors')}`
}

function loginConnectHref(provider: ProviderDefinition, scope: Scope) {
  const search = new URLSearchParams({
    return_to: '/connectors',
    post_auth_action: 'connect_provider',
    owner_scope: scope,
    provider: provider.path,
  })
  return `/login?${search.toString()}`
}

function providerActionLabel(provider: ProviderDefinition, scope: Scope) {
  return `${scope === 'workspace' ? '조직' : '내'} ${provider.label} 연결`
}

function templateBadgeLabel(provider: ProviderDefinition, templateId: string, scope: Scope) {
  const template = provider.templates.find((item) => item.id === templateId)
  if (!template) return templateId
  return scope === 'workspace' ? template.organizationLabel : template.personalLabel
}

function providerReadyMessage(provider: ProviderDefinition, scope: Scope, oauthConfigured: boolean, connected: boolean) {
  if (!oauthConfigured) {
    return '서비스 운영자가 OAuth 설정을 마치면 이 데이터 소스를 바로 연결할 수 있습니다.'
  }
  if (connected) {
    return scope === 'workspace'
      ? '조직 문서가 기존 저장소와 검색 흐름에 자동으로 반영됩니다.'
      : '개인 문서는 필요할 때만 보조적으로 동기화할 수 있습니다.'
  }
  return scope === 'workspace' ? provider.organizationDescription : provider.personalDescription
}

function formatSetupStateLabel(value: string) {
  if (value === 'ready') return '운영 가능'
  if (value === 'attention_required') return '조치 필요'
  if (value === 'setup_needed') return '초기 설정 필요'
  if (value === 'not_configured') return '미준비'
  return '확인 중'
}

function SyncSummary({ summary }: { summary: Record<string, number> }) {
  const entries = [
    ['imported', '가져옴'],
    ['unchanged', '변경 없음'],
    ['unsupported', '지원 안 함'],
    ['failed', '실패'],
    ['deleted', '사라짐'],
  ] as const

  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([key, label]) => (
        <Badge key={key}>
          {label} {Number(summary[key] ?? 0)}
        </Badge>
      ))}
    </div>
  )
}

function ProviderCard({
  provider,
  scope,
  readiness,
  connection,
  canManage,
  authenticated,
}: {
  provider: ProviderDefinition
  scope: Scope
  readiness?: ConnectorProviderReadiness | null
  connection?: ConnectorConnectionSummary | null
  canManage: boolean
  authenticated: boolean
}) {
  const Icon = provider.icon
  const oauthConfigured = readiness?.oauth_configured === true
  const connected = Boolean(connection)
  const needsReauth = connection?.status === 'needs_reauth'
  const href = authenticated ? connectHref(provider, scope) : loginConnectHref(provider, scope)
  const resourceCount = connection?.resources.length ?? 0
  const workspaceReadOnly = scope === 'workspace' && authenticated && !canManage

  let action: ReactNode = null
  if (!oauthConfigured) {
    action = <Badge>미준비</Badge>
  } else if (!authenticated) {
    action = (
      <Button size="sm" onClick={() => window.location.assign(href)}>
        {providerActionLabel(provider, scope)}
      </Button>
    )
  } else if (connected && needsReauth && canManage) {
    action = (
      <Button size="sm" onClick={() => window.location.assign(href)}>
        다시 연결
      </Button>
    )
  } else if (!connected && canManage) {
    action = (
      <Button size="sm" onClick={() => window.location.assign(href)}>
        {providerActionLabel(provider, scope)}
      </Button>
    )
  } else if (connected) {
    action = <Badge>{needsReauth ? '재연결 필요' : '연결됨'}</Badge>
  } else if (workspaceReadOnly) {
    action = <Badge>관리자 권한 필요</Badge>
  } else {
    action = (
      <Button size="sm" onClick={() => window.location.assign(href)}>
        {providerActionLabel(provider, scope)}
      </Button>
    )
  }

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950/30 dark:text-blue-300">
            <Icon className="size-5" />
          </div>
          <div>
            <div className="text-base font-semibold text-neutral-950 dark:text-neutral-50">{provider.label}</div>
            <div className="text-xs text-neutral-400">{scope === 'workspace' ? '조직 데이터 소스' : '개인 보조 소스'}</div>
          </div>
        </div>
        {action}
      </div>
      <div className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
        <div>{providerReadyMessage(provider, scope, oauthConfigured, connected)}</div>
        {!authenticated && oauthConfigured ? <div className="text-xs text-neutral-400">로그인 후 바로 연결 단계로 이어집니다.</div> : null}
        {workspaceReadOnly ? <div className="text-xs text-neutral-400">조직 연결은 워크스페이스 관리자만 만들거나 다시 연결할 수 있습니다.</div> : null}
        {scope === 'workspace' && readiness ? (
          <div className="flex flex-wrap gap-2">
            <Badge>{formatSetupStateLabel(readiness.setup_state)}</Badge>
            <Badge>정상 {readiness.healthy_source_count}</Badge>
            <Badge>주의 {readiness.needs_attention_count}</Badge>
            {readiness.recommended_templates.map((template) => (
              <Badge key={template}>{templateBadgeLabel(provider, template, scope)}</Badge>
            ))}
          </div>
        ) : null}
        {connection ? (
          <div className="flex flex-wrap gap-2">
            <Badge>{formatConnectorStatusLabel(connection.status)}</Badge>
            <Badge>{resourceCount}개 항목 연결</Badge>
            {connection.account_email ? <Badge>{connection.account_email}</Badge> : null}
          </div>
        ) : null}
      </div>
    </Card>
  )
}

function ResourceRow({
  connection,
  resource,
  canManage,
}: {
  connection: ConnectorConnectionSummary
  resource: ConnectorResourceSummary
  canManage: boolean
}) {
  const queryClient = useQueryClient()
  const [syncMode, setSyncMode] = useState<SyncMode>(resource.sync_mode === 'auto' ? 'auto' : 'manual')
  const [intervalMinutes, setIntervalMinutes] = useState<number>(resource.sync_interval_minutes ?? 60)

  const updateMutation = useMutation({
    mutationFn: async (payload: { sync_mode: SyncMode; sync_interval_minutes: number | null }) =>
      fetchJson<ConnectorResourceSummary>(`/api/connectors/${connection.id}/resources/${resource.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    onSuccess: async (updated) => {
      setSyncMode(updated.sync_mode === 'auto' ? 'auto' : 'manual')
      setIntervalMinutes(updated.sync_interval_minutes ?? 60)
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
    },
  })

  const syncMutation = useMutation({
    mutationFn: async () =>
      fetchJson<JobSummary>(`/api/connectors/${connection.id}/resources/${resource.id}/sync`, {
        method: 'POST',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
      await queryClient.invalidateQueries({ queryKey: ['connector-items', connection.id] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () =>
      fetchJson<void>(`/api/connectors/${connection.id}/resources/${resource.id}`, {
        method: 'DELETE',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
      await queryClient.invalidateQueries({ queryKey: ['connector-items', connection.id] })
    },
  })

  return (
    <tr className="border-t border-neutral-200 align-top dark:border-neutral-800">
      <td className="px-4 py-4">
        <div className="space-y-1">
          <div className="font-medium text-neutral-900 dark:text-neutral-50">{resource.name}</div>
          <div className="flex flex-wrap gap-2 text-xs text-neutral-400">
            <span>{formatConnectorProviderLabel(connection.provider)}</span>
            <span>·</span>
            <span>{formatConnectorResourceKindLabel(resource.resource_kind)}</span>
            <span>·</span>
            <span>{formatStatusLabel(resource.status)}</span>
          </div>
          {resource.resource_url ? (
            <Link
              href={resource.resource_url}
              target="_blank"
              className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400"
            >
              원본 열기 <ExternalLink className="size-3.5" />
            </Link>
          ) : null}
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="text-sm text-neutral-600 dark:text-neutral-400">
          <div>{formatConnectorSyncModeLabel(syncMode)}</div>
          {resource.sync_children ? <div className="mt-1 text-xs text-neutral-400">하위 항목 포함</div> : null}
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="space-y-2">
          <select
            className={selectClassName}
            disabled={!canManage || updateMutation.isPending}
            value={syncMode}
            onChange={(event) => {
              const nextMode = event.target.value as SyncMode
              setSyncMode(nextMode)
              updateMutation.mutate({
                sync_mode: nextMode,
                sync_interval_minutes: nextMode === 'auto' ? intervalMinutes : null,
              })
            }}
          >
            <option value="manual">수동</option>
            <option value="auto">자동</option>
          </select>
          <select
            className={selectClassName}
            disabled={!canManage || syncMode !== 'auto' || updateMutation.isPending}
            value={String(intervalMinutes)}
            onChange={(event) => {
              const nextInterval = Number(event.target.value)
              setIntervalMinutes(nextInterval)
              updateMutation.mutate({
                sync_mode: 'auto',
                sync_interval_minutes: nextInterval,
              })
            }}
          >
            {intervalOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
          <div>최근 시작 {formatDate(resource.last_sync_started_at)}</div>
          <div>최근 완료 {formatDate(resource.last_sync_completed_at)}</div>
          {resource.next_auto_sync_at ? <div>다음 자동 {formatDate(resource.next_auto_sync_at)}</div> : null}
          <SyncSummary summary={resource.last_sync_summary || {}} />
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={!canManage || syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
          >
            {syncMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <RefreshCcw className="size-4" />}
            지금 동기화
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={!canManage || deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            <Trash2 className="size-4" /> 삭제
          </Button>
        </div>
        {updateMutation.error ? (
          <div className="mt-2 text-xs text-red-600 dark:text-red-400">
            {updateMutation.error instanceof Error ? updateMutation.error.message : '설정을 바꾸지 못했습니다.'}
          </div>
        ) : null}
        {syncMutation.error ? (
          <div className="mt-2 text-xs text-red-600 dark:text-red-400">
            {syncMutation.error instanceof Error ? syncMutation.error.message : '동기화를 요청하지 못했습니다.'}
          </div>
        ) : null}
      </td>
    </tr>
  )
}

function ResourceTable({
  title,
  records,
  canManage,
}: {
  title: string
  records: ResourceRecord[]
  canManage: boolean
}) {
  return (
    <Card className="p-5">
      <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">{title}</div>
      {records.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
          아직 연결된 항목이 없습니다.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
                <th className="px-4 pb-3 font-medium">가져올 항목</th>
                <th className="px-4 pb-3 font-medium">동기화 방식</th>
                <th className="px-4 pb-3 font-medium">주기</th>
                <th className="px-4 pb-3 font-medium">최근 상태</th>
                <th className="px-4 pb-3 font-medium">관리</th>
              </tr>
            </thead>
            <tbody>
              {records.map(({ connection, resource }) => (
                <ResourceRow key={resource.id} connection={connection} resource={resource} canManage={canManage} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function ConnectedResourcesList({
  title,
  records,
}: {
  title: string
  records: ResourceRecord[]
}) {
  return (
    <Card className="p-5">
      <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">{title}</div>
      {records.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
          아직 조직에서 제공 중인 데이터 소스가 없습니다.
        </div>
      ) : (
        <div className="space-y-3">
          {records.map(({ connection, resource }) => (
            <div key={resource.id} className="rounded-2xl border border-neutral-200 px-4 py-4 dark:border-neutral-800">
              <div className="flex flex-wrap items-center gap-2">
                <div className="font-medium text-neutral-900 dark:text-neutral-50">{resource.name}</div>
                <Badge>{formatConnectorProviderLabel(connection.provider)}</Badge>
                <Badge>{formatConnectorResourceKindLabel(resource.resource_kind)}</Badge>
                <Badge>{formatStatusLabel(resource.status)}</Badge>
              </div>
              <div className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
                동기화 {formatConnectorSyncModeLabel(resource.sync_mode)} · 최근 완료 {formatDate(resource.last_sync_completed_at)}
              </div>
              {resource.resource_url ? (
                <Link
                  href={resource.resource_url}
                  target="_blank"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400"
                >
                  원본 열기 <ExternalLink className="size-3.5" />
                </Link>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function TemplateCard({
  template,
  scope,
  active,
  onSelect,
}: {
  template: ProviderTemplate
  scope: Scope
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`rounded-2xl border p-4 text-left transition ${
        active
          ? 'border-blue-500 bg-blue-50/70 dark:border-blue-500 dark:bg-blue-950/20'
          : 'border-neutral-200 hover:border-blue-300 dark:border-neutral-800 dark:hover:border-blue-700'
      }`}
    >
      <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">{templateLabel(template, scope)}</div>
      <div className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">{template.description}</div>
    </button>
  )
}

function ConnectionManager({
  connection,
  canManage,
}: {
  connection: ConnectorConnectionSummary
  canManage: boolean
}) {
  const queryClient = useQueryClient()
  const provider = providerDefinition(connection.provider)
  const [resourceKind, setResourceKind] = useState<ResourceKind>(provider.templates[0]?.resourceKind ?? 'folder')
  const [externalId, setExternalId] = useState('')
  const [resourceName, setResourceName] = useState('')
  const [resourceUrl, setResourceUrl] = useState('')
  const [parentExternalId, setParentExternalId] = useState('')
  const [providerMetadata, setProviderMetadata] = useState<Record<string, unknown>>({})
  const [syncChildren, setSyncChildren] = useState(provider.key === 'google_drive')
  const [syncMode, setSyncMode] = useState<SyncMode>(connection.owner_scope === 'workspace' ? 'auto' : 'manual')
  const [syncIntervalMinutes, setSyncIntervalMinutes] = useState(60)
  const [showItems, setShowItems] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showInternalDetails, setShowInternalDetails] = useState(false)
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null)

  const [googleBrowseKind, setGoogleBrowseKind] = useState<GoogleResourceKind>('folder')
  const [googleParentId, setGoogleParentId] = useState<string | null>(null)
  const [googleContainerId, setGoogleContainerId] = useState<string | null>(null)
  const [googleHistory, setGoogleHistory] = useState<Array<{ kind: GoogleResourceKind; parentId: string | null; containerId: string | null }>>([])
  const [googleBrowseItems, setGoogleBrowseItems] = useState<ConnectorBrowseItem[]>([])
  const [googleBrowseLoading, setGoogleBrowseLoading] = useState(false)
  const [googleBrowseError, setGoogleBrowseError] = useState<string | null>(null)

  const [notionQuery, setNotionQuery] = useState('')
  const [notionResults, setNotionResults] = useState<ConnectorBrowseItem[]>([])
  const [notionCursor, setNotionCursor] = useState<string | null>(null)
  const [notionHasMore, setNotionHasMore] = useState(false)
  const [notionLoading, setNotionLoading] = useState(false)
  const [notionError, setNotionError] = useState<string | null>(null)

  const selectedTemplate = provider.templates.find((item) => item.id === activeTemplateId) ?? null

  const itemsQuery = useQuery({
    queryKey: ['connector-items', connection.id],
    queryFn: () => fetchJson<ConnectorSourceItemSummary[]>(`/api/connectors/${connection.id}/items`),
    enabled: showItems,
  })

  const createResourceMutation = useMutation({
    mutationFn: async () =>
      fetchJson<ConnectorResourceSummary>(`/api/connectors/${connection.id}/resources`, {
        method: 'POST',
        body: JSON.stringify({
          resource_kind: resourceKind,
          external_id: externalId,
          name: resourceName,
          resource_url: resourceUrl || null,
          parent_external_id: parentExternalId || null,
          sync_children: connection.provider === 'google_drive' ? syncChildren : resourceKind === 'database',
          sync_mode: syncMode,
          sync_interval_minutes: syncMode === 'auto' ? syncIntervalMinutes : null,
          provider_metadata: providerMetadata,
        } satisfies ConnectorResourceCreateRequest),
      }),
    onSuccess: async () => {
      setExternalId('')
      setResourceName('')
      setResourceUrl('')
      setParentExternalId('')
      setProviderMetadata({})
      setShowInternalDetails(false)
      if (connection.provider === 'google_drive') {
        setGoogleBrowseItems([])
        setGoogleParentId(null)
        setGoogleContainerId(null)
        setGoogleHistory([])
      } else {
        setNotionResults([])
        setNotionCursor(null)
        setNotionHasMore(false)
      }
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
    },
  })

  const deleteConnectionMutation = useMutation({
    mutationFn: async () =>
      fetchJson<void>(`/api/connectors/${connection.id}`, {
        method: 'DELETE',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
    },
  })

  async function loadGoogleBrowse(kind: GoogleResourceKind, options?: { parentId?: string | null; containerId?: string | null }) {
    setGoogleBrowseLoading(true)
    setGoogleBrowseError(null)
    try {
      const search = new URLSearchParams({ kind })
      if (options?.parentId) search.set('parent_id', options.parentId)
      if (options?.containerId) search.set('container_id', options.containerId)
      const payload = await fetchJson<ConnectorBrowseResponse>(`/api/connectors/${connection.id}/browse?${search.toString()}`)
      setGoogleBrowseKind(kind)
      setGoogleParentId(options?.parentId ?? null)
      setGoogleContainerId(options?.containerId ?? null)
      setGoogleBrowseItems(payload.items)
    } catch (error) {
      setGoogleBrowseError(error instanceof Error ? error.message : 'Google Drive 항목을 불러오지 못했습니다.')
    } finally {
      setGoogleBrowseLoading(false)
    }
  }

  async function searchNotion(kind: NotionResourceKind, cursor?: string | null, queryOverride?: string) {
    setNotionLoading(true)
    setNotionError(null)
    try {
      const search = new URLSearchParams({ kind })
      const queryText = queryOverride ?? notionQuery.trim()
      if (queryText) search.set('query', queryText)
      if (cursor) search.set('cursor', cursor)
      const payload = await fetchJson<ConnectorBrowseResponse>(`/api/connectors/${connection.id}/browse?${search.toString()}`)
      setNotionResults((current) => (cursor ? [...current, ...payload.items] : payload.items))
      setNotionCursor(payload.cursor ?? null)
      setNotionHasMore(payload.has_more)
    } catch (error) {
      setNotionError(error instanceof Error ? error.message : 'Notion 항목을 불러오지 못했습니다.')
    } finally {
      setNotionLoading(false)
    }
  }

  function applySelectedItem(item: ConnectorBrowseItem) {
    setResourceKind(item.resource_kind as ResourceKind)
    setExternalId(item.id)
    setResourceName(item.name)
    setResourceUrl(item.resource_url ?? '')
    setParentExternalId(item.parent_external_id ?? '')
    setProviderMetadata(item.provider_metadata)
    setSyncChildren(connection.provider === 'google_drive' ? true : item.resource_kind === 'database')
  }

  function activateTemplate(template: ProviderTemplate) {
    setShowAdvanced(true)
    setActiveTemplateId(template.id)
    setShowInternalDetails(false)
    setExternalId('')
    setResourceName('')
    setResourceUrl('')
    setParentExternalId('')
    setProviderMetadata({})
    setResourceKind(template.resourceKind)
    setSyncChildren(connection.provider === 'google_drive' ? true : template.resourceKind === 'database')
    if (connection.provider === 'google_drive') {
      setGoogleHistory([])
      setGoogleBrowseItems([])
      setGoogleParentId(null)
      setGoogleContainerId(null)
      loadGoogleBrowse(template.resourceKind as GoogleResourceKind)
      return
    }
    setNotionQuery('')
    setNotionResults([])
    setNotionCursor(null)
    setNotionHasMore(false)
    searchNotion(template.resourceKind as NotionResourceKind, null, '')
  }

  const visibleItems = useMemo(() => itemsQuery.data?.slice(0, 8) ?? [], [itemsQuery.data])

  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-lg font-semibold text-neutral-950 dark:text-neutral-50">{connection.display_name}</div>
            <Badge>{formatConnectorProviderLabel(connection.provider)}</Badge>
            <Badge>{connection.owner_scope === 'workspace' ? '조직 연결' : '내 연결'}</Badge>
            <Badge>{formatConnectorStatusLabel(connection.status)}</Badge>
          </div>
          <div className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{connection.account_email || '계정 이메일 정보 없음'}</div>
          <div className="mt-1 text-xs text-neutral-400">
            최근 검증 {formatDate(connection.last_validated_at)} · 연결 생성 {formatDate(connection.created_at)}
          </div>
        </div>
        {canManage ? (
          <Button
            size="sm"
            variant="ghost"
            disabled={deleteConnectionMutation.isPending}
            onClick={() => deleteConnectionMutation.mutate()}
          >
            <Trash2 className="size-4" /> 연결 삭제
          </Button>
        ) : null}
      </div>

      <div className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">빠른 연결 템플릿</div>
            <div className="mt-1 text-sm text-neutral-500">
              자주 쓰는 흐름만 먼저 노출합니다. 세부 선택은 아래 고급 모드에서 이어집니다.
            </div>
          </div>
          <Badge>{provider.description}</Badge>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {provider.templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              scope={connection.owner_scope as Scope}
              active={template.id === activeTemplateId}
              onSelect={() => activateTemplate(template)}
            />
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-neutral-50 px-4 py-3 text-sm text-neutral-600 dark:bg-neutral-900/60 dark:text-neutral-400">
          <div>
            {showAdvanced
              ? '고급 모드가 열려 있습니다. 항목을 선택하고 동기화 방식을 정할 수 있습니다.'
              : '고급 모드는 선택기와 세부 설정을 열 때만 사용합니다.'}
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowAdvanced((value) => !value)}>
            {showAdvanced ? '고급 모드 닫기' : '고급 모드 열기'}
          </Button>
        </div>

        {showAdvanced ? (
          <div className="mt-4 rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">가져올 항목 선택</div>
                <div className="mt-1 text-sm text-neutral-500">
                  {selectedTemplate
                    ? `${templateLabel(selectedTemplate, connection.owner_scope as Scope)} 템플릿으로 항목을 고르는 중입니다.`
                    : '템플릿을 먼저 고르면 항목 선택기가 열립니다.'}
                </div>
              </div>
              {selectedTemplate ? <Badge>{templateLabel(selectedTemplate, connection.owner_scope as Scope)}</Badge> : null}
            </div>

            {connection.provider === 'google_drive' ? (
              <div className="space-y-4">
                {!selectedTemplate ? (
                  <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
                    위 템플릿에서 공유 드라이브 또는 팀 폴더를 먼저 선택해 주세요.
                  </div>
                ) : (
                  <>
                    {googleBrowseItems.length > 0 ? (
                      <div className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                          <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">
                            {googleBrowseKind === 'shared_drive' ? '공유 드라이브 선택' : '폴더 선택'}
                          </div>
                          {googleHistory.length > 0 ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                const previous = googleHistory[googleHistory.length - 1]
                                setGoogleHistory((items) => items.slice(0, -1))
                                loadGoogleBrowse(previous.kind, {
                                  parentId: previous.parentId,
                                  containerId: previous.containerId,
                                })
                              }}
                            >
                              이전 단계
                            </Button>
                          ) : null}
                        </div>
                        <div className="space-y-2">
                          {googleBrowseItems.map((item) => {
                            const driveId = typeof item.provider_metadata.drive_id === 'string' ? item.provider_metadata.drive_id : null
                            return (
                              <div
                                key={item.id}
                                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800"
                              >
                                <div>
                                  <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">{item.name}</div>
                                  <div className="mt-1 text-xs text-neutral-400">
                                    {item.resource_kind === 'shared_drive' ? '공유 드라이브 전체 문서' : '선택한 폴더와 하위 폴더 문서'}
                                  </div>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  <Button size="sm" variant="outline" onClick={() => applySelectedItem(item)}>
                                    선택
                                  </Button>
                                  {item.resource_kind === 'shared_drive' ? (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => {
                                        setGoogleHistory((items) => [
                                          ...items,
                                          { kind: googleBrowseKind, parentId: googleParentId, containerId: googleContainerId },
                                        ])
                                        loadGoogleBrowse('folder', { parentId: null, containerId: item.id })
                                      }}
                                    >
                                      열기 <ArrowRight className="size-4" />
                                    </Button>
                                  ) : item.has_children ? (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => {
                                        setGoogleHistory((items) => [
                                          ...items,
                                          { kind: googleBrowseKind, parentId: googleParentId, containerId: googleContainerId },
                                        ])
                                        loadGoogleBrowse('folder', { parentId: item.id, containerId: driveId ?? googleContainerId })
                                      }}
                                    >
                                      열기 <ArrowRight className="size-4" />
                                    </Button>
                                  ) : null}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ) : null}

                    {googleBrowseLoading ? (
                      <div className="flex items-center gap-2 text-sm text-neutral-500">
                        <LoaderCircle className="size-4 animate-spin" /> Google Drive 항목을 불러오는 중입니다.
                      </div>
                    ) : null}
                    {googleBrowseError ? <div className="text-sm text-red-600 dark:text-red-400">{googleBrowseError}</div> : null}
                  </>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {!selectedTemplate ? (
                  <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
                    위 템플릿에서 페이지 또는 데이터베이스를 먼저 선택해 주세요.
                  </div>
                ) : (
                  <>
                    <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-300">
                      이 integration과 공유된 항목만 보입니다. 원하는 항목이 없다면 Notion에서 먼저 공유한 뒤 새로고침해 주세요.
                    </div>
                    <div className="grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
                      <label className="space-y-2 text-sm">
                        <div className="font-medium text-neutral-700 dark:text-neutral-300">검색어</div>
                        <Input
                          value={notionQuery}
                          onChange={(event) => setNotionQuery(event.target.value)}
                          placeholder="페이지 제목 또는 데이터베이스 이름"
                          disabled={!canManage}
                        />
                      </label>
                      <div className="flex items-end">
                        <Button
                          disabled={!canManage || notionLoading}
                          onClick={() => {
                            setNotionResults([])
                            setNotionCursor(null)
                            setNotionHasMore(false)
                            searchNotion(resourceKind as NotionResourceKind)
                          }}
                        >
                          {notionLoading ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
                          검색
                        </Button>
                      </div>
                      <div className="flex items-end">
                        <Button
                          variant="outline"
                          disabled={!canManage || notionLoading}
                          onClick={() => {
                            setNotionQuery('')
                            setNotionResults([])
                            setNotionCursor(null)
                            setNotionHasMore(false)
                            searchNotion(resourceKind as NotionResourceKind, null, '')
                          }}
                        >
                          최근 항목
                        </Button>
                      </div>
                      <div className="flex items-end">
                        <Button
                          variant="ghost"
                          disabled={!canManage || notionLoading}
                          onClick={() => {
                            setNotionResults([])
                            setNotionCursor(null)
                            setNotionHasMore(false)
                            searchNotion(resourceKind as NotionResourceKind)
                          }}
                        >
                          <RefreshCcw className="size-4" /> 새로고침
                        </Button>
                      </div>
                    </div>

                    {notionResults.length > 0 ? (
                      <div className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
                        <div className="mb-3 text-sm font-medium text-neutral-900 dark:text-neutral-50">
                          {resourceKind === 'database' ? '데이터베이스 선택' : '페이지 선택'}
                        </div>
                        <div className="space-y-2">
                          {notionResults.map((item) => (
                            <div
                              key={item.id}
                              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800"
                            >
                              <div>
                                <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">{item.name}</div>
                                <div className="mt-1 text-xs text-neutral-400">
                                  {item.resource_kind === 'database' ? '하위 페이지 전체를 동기화' : '선택한 페이지 1개만 동기화'}
                                </div>
                              </div>
                              <Button size="sm" variant="outline" onClick={() => applySelectedItem(item)}>
                                선택
                              </Button>
                            </div>
                          ))}
                        </div>
                        {notionHasMore ? (
                          <div className="mt-3">
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={!notionCursor || notionLoading}
                              onClick={() => searchNotion(resourceKind as NotionResourceKind, notionCursor)}
                            >
                              더 보기
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    ) : null}

                    {notionError ? <div className="text-sm text-red-600 dark:text-red-400">{notionError}</div> : null}
                  </>
                )}
              </div>
            )}

            {externalId ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
                  <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">선택한 항목</div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <div className="font-medium text-neutral-900 dark:text-neutral-50">{resourceName}</div>
                    <Badge>{formatConnectorResourceKindLabel(resourceKind)}</Badge>
                    {resourceUrl ? (
                      <Link href={resourceUrl} target="_blank" className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                        원본 열기 <ExternalLink className="size-3.5" />
                      </Link>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
                  <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">동기화 설정</div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="space-y-2 text-sm">
                      <div className="font-medium text-neutral-700 dark:text-neutral-300">동기화 방식</div>
                      <select
                        className={selectClassName}
                        value={syncMode}
                        disabled={!canManage}
                        onChange={(event) => setSyncMode(event.target.value as SyncMode)}
                      >
                        <option value="manual">수동</option>
                        <option value="auto">자동</option>
                      </select>
                    </label>
                    <label className="space-y-2 text-sm">
                      <div className="font-medium text-neutral-700 dark:text-neutral-300">자동 주기</div>
                      <select
                        className={selectClassName}
                        value={String(syncIntervalMinutes)}
                        disabled={!canManage || syncMode !== 'auto'}
                        onChange={(event) => setSyncIntervalMinutes(Number(event.target.value))}
                      >
                        {intervalOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  {connection.provider === 'google_drive' && resourceKind === 'folder' ? (
                    <label className="mt-3 flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                      <input
                        type="checkbox"
                        checked={syncChildren}
                        disabled={!canManage}
                        onChange={(event) => setSyncChildren(event.target.checked)}
                      />
                      하위 폴더까지 포함
                    </label>
                  ) : (
                    <div className="mt-3 text-sm text-neutral-500">
                      {resourceKind === 'database' ? '데이터베이스는 하위 페이지를 함께 가져옵니다.' : '선택한 항목만 동기화됩니다.'}
                    </div>
                  )}

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      disabled={!canManage || !externalId.trim() || !resourceName.trim() || createResourceMutation.isPending}
                      onClick={() => createResourceMutation.mutate()}
                    >
                      {createResourceMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
                      이 항목 연결
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setShowInternalDetails((value) => !value)}>
                      {showInternalDetails ? '세부 정보 숨기기' : '세부 정보 보기'}
                    </Button>
                  </div>

                  {showInternalDetails ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <label className="space-y-2 text-sm">
                        <div className="font-medium text-neutral-700 dark:text-neutral-300">리소스 이름</div>
                        <Input value={resourceName} readOnly disabled />
                      </label>
                      <label className="space-y-2 text-sm">
                        <div className="font-medium text-neutral-700 dark:text-neutral-300">외부 ID</div>
                        <Input value={externalId} readOnly disabled />
                      </label>
                      <label className="space-y-2 text-sm">
                        <div className="font-medium text-neutral-700 dark:text-neutral-300">원본 주소</div>
                        <Input value={resourceUrl} readOnly disabled />
                      </label>
                      <label className="space-y-2 text-sm">
                        <div className="font-medium text-neutral-700 dark:text-neutral-300">상위 ID</div>
                        <Input value={parentExternalId} readOnly disabled />
                      </label>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            {createResourceMutation.error ? (
              <div className="mt-3 text-sm text-red-600 dark:text-red-400">
                {createResourceMutation.error instanceof Error ? createResourceMutation.error.message : '항목을 연결하지 못했습니다.'}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="mt-5 rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">최근 동기화 항목</div>
          <Button size="sm" variant="ghost" onClick={() => setShowItems((value) => !value)}>
            {showItems ? '숨기기' : '항목 보기'}
          </Button>
        </div>
        {showItems ? (
          itemsQuery.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-neutral-500">
              <LoaderCircle className="size-4 animate-spin" /> 동기화 항목을 불러오는 중입니다.
            </div>
          ) : itemsQuery.error ? (
            <div className="text-sm text-red-600 dark:text-red-400">
              {itemsQuery.error instanceof Error ? itemsQuery.error.message : '동기화 항목을 불러오지 못했습니다.'}
            </div>
          ) : visibleItems.length === 0 ? (
            <div className="text-sm text-neutral-500">아직 동기화된 항목이 없습니다.</div>
          ) : (
            <div className="space-y-2">
              {visibleItems.map((item) => (
                <div key={item.id} className="rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">{item.name}</div>
                    <Badge>{formatConnectorItemStatusLabel(item.item_status)}</Badge>
                    {item.mime_type ? <Badge>{item.mime_type}</Badge> : null}
                  </div>
                  <div className="mt-1 text-xs text-neutral-400">최근 확인 {formatDate(item.last_synced_at)}</div>
                  {item.source_url ? (
                    <Link href={item.source_url} target="_blank" className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                      원본 열기 <ExternalLink className="size-3.5" />
                    </Link>
                  ) : null}
                  {item.unsupported_reason ? <div className="mt-2 text-sm text-amber-600 dark:text-amber-400">{item.unsupported_reason}</div> : null}
                  {item.error_message ? <div className="mt-2 text-sm text-red-600 dark:text-red-400">{item.error_message}</div> : null}
                </div>
              ))}
            </div>
          )
        ) : (
          <div className="text-sm text-neutral-500">최근 가져온 항목 상태를 확인하려면 항목 보기를 누르세요.</div>
        )}
      </div>
    </Card>
  )
}

function WorkspaceInvitePanel({
  invitations,
  isLoading,
  error,
  createError,
  onCreate,
  isCreating,
}: {
  invitations: WorkspaceInvitationSummary[]
  isLoading: boolean
  error: string | null
  createError: string | null
  onCreate: (payload: { invited_email: string; role: string }) => Promise<WorkspaceInvitationCreateResponse>
  isCreating: boolean
}) {
  const [invitedEmail, setInvitedEmail] = useState('')
  const [role, setRole] = useState('member')
  const [createdInviteUrl, setCreatedInviteUrl] = useState<string | null>(null)
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const recentInvitations = invitations.slice(0, 5)

  async function handleCreate() {
    try {
      const payload = await onCreate({
        invited_email: invitedEmail,
        role,
      })
      setCreatedInviteUrl(payload.invite_url)
      setInvitedEmail('')
      setRole('member')
      setCopyMessage(null)
    } catch {
      // mutation state is rendered by the parent component
    }
  }

  async function copyLink(value: string) {
    try {
      await navigator.clipboard.writeText(value)
      setCopyMessage('초대 링크를 복사했습니다.')
    } catch {
      setCopyMessage('브라우저에서 복사하지 못했습니다. 링크를 직접 복사해 주세요.')
    }
  }

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        <UserPlus className="size-4 text-blue-500" /> 워크스페이스 초대
      </div>
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_auto]">
        <label className="space-y-2 text-sm">
          <div className="font-medium text-neutral-700 dark:text-neutral-300">초대할 이메일</div>
          <Input
            type="email"
            value={invitedEmail}
            onChange={(event) => setInvitedEmail(event.target.value)}
            placeholder="team@example.com"
            disabled={isCreating}
          />
        </label>
        <label className="space-y-2 text-sm">
          <div className="font-medium text-neutral-700 dark:text-neutral-300">역할</div>
          <select className={selectClassName} value={role} onChange={(event) => setRole(event.target.value)} disabled={isCreating}>
            <option value="member">member</option>
            <option value="admin">admin</option>
            <option value="owner">owner</option>
          </select>
        </label>
        <div className="flex items-end">
          <Button disabled={!invitedEmail.trim() || isCreating} onClick={() => void handleCreate()}>
            {isCreating ? <LoaderCircle className="size-4 animate-spin" /> : <UserPlus className="size-4" />}
            초대 링크 만들기
          </Button>
        </div>
      </div>

      <div className="mt-3 text-sm text-neutral-500">
        이메일 발송은 하지 않습니다. 생성된 링크를 복사해 전달하면 됩니다.
      </div>

      {createdInviteUrl ? (
        <div className="mt-4 rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
          <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">방금 만든 초대 링크</div>
          <div className="mt-2 break-all rounded-xl bg-neutral-50 px-3 py-2 text-sm text-neutral-600 dark:bg-neutral-900 dark:text-neutral-300">
            {createdInviteUrl}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => void copyLink(createdInviteUrl)}>
              <Copy className="size-4" /> 링크 복사
            </Button>
            {copyMessage ? <span className="text-xs text-neutral-500">{copyMessage}</span> : null}
          </div>
        </div>
      ) : null}

      {createError ? <div className="mt-4 text-sm text-red-600 dark:text-red-400">{createError}</div> : null}

      <div className="mt-5">
        <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">최근 초대</div>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 최근 초대를 불러오는 중입니다.
          </div>
        ) : error ? (
          <div className="text-sm text-red-600 dark:text-red-400">{error}</div>
        ) : recentInvitations.length === 0 ? (
          <div className="text-sm text-neutral-500">아직 생성한 초대 링크가 없습니다.</div>
        ) : (
          <div className="space-y-2">
            {recentInvitations.map((invitation) => (
              <div key={invitation.id} className="rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="font-medium text-neutral-900 dark:text-neutral-50">{invitation.invited_email}</div>
                  <Badge>{invitation.role}</Badge>
                  <Badge>{invitation.accepted_at ? '수락됨' : '대기 중'}</Badge>
                </div>
                <div className="mt-1 text-xs text-neutral-400">
                  생성 {formatDate(invitation.created_at)} · 만료 {formatDate(invitation.expires_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function WorkspaceAccessPanel({
  members,
  isLoading,
  error,
  onCreateResetLink,
  isCreatingResetLink,
  createResetError,
}: {
  members: WorkspaceMemberSummary[]
  isLoading: boolean
  error: string | null
  onCreateResetLink: (email: string) => Promise<PasswordResetLinkCreateResponse>
  isCreatingResetLink: boolean
  createResetError: string | null
}) {
  const [createdResetUrl, setCreatedResetUrl] = useState<string | null>(null)
  const [createdResetEmail, setCreatedResetEmail] = useState<string | null>(null)
  const [copyMessage, setCopyMessage] = useState<string | null>(null)

  async function handleCreateResetLink(email: string) {
    try {
      const payload = await onCreateResetLink(email)
      setCreatedResetUrl(payload.reset_url)
      setCreatedResetEmail(payload.email)
      setCopyMessage(null)
    } catch {
      // mutation state is rendered by the parent component
    }
  }

  async function copyLink(value: string) {
    try {
      await navigator.clipboard.writeText(value)
      setCopyMessage('재설정 링크를 복사했습니다.')
    } catch {
      setCopyMessage('브라우저에서 복사하지 못했습니다. 링크를 직접 복사해 주세요.')
    }
  }

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        <ShieldCheck className="size-4 text-blue-500" /> 접근 관리
      </div>

      <div className="text-sm text-neutral-500">
        워크스페이스 멤버를 확인하고, 필요한 경우 비밀번호 재설정 링크를 만들어 전달할 수 있습니다.
      </div>

      {createdResetUrl ? (
        <div className="mt-4 rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
          <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">
            {createdResetEmail} 비밀번호 재설정 링크
          </div>
          <div className="mt-2 break-all rounded-xl bg-neutral-50 px-3 py-2 text-sm text-neutral-600 dark:bg-neutral-900 dark:text-neutral-300">
            {createdResetUrl}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => void copyLink(createdResetUrl)}>
              <Copy className="size-4" /> 링크 복사
            </Button>
            {copyMessage ? <span className="text-xs text-neutral-500">{copyMessage}</span> : null}
          </div>
        </div>
      ) : null}

      {createResetError ? <div className="mt-4 text-sm text-red-600 dark:text-red-400">{createResetError}</div> : null}

      <div className="mt-5">
        <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">워크스페이스 멤버</div>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 멤버 목록을 불러오는 중입니다.
          </div>
        ) : error ? (
          <div className="text-sm text-red-600 dark:text-red-400">{error}</div>
        ) : members.length === 0 ? (
          <div className="text-sm text-neutral-500">아직 워크스페이스 멤버가 없습니다.</div>
        ) : (
          <div className="space-y-2">
            {members.map((member) => (
              <div key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="font-medium text-neutral-900 dark:text-neutral-50">{member.name}</div>
                    <Badge>{member.role}</Badge>
                  </div>
                  <div className="mt-1 text-sm text-neutral-500">{member.email}</div>
                </div>
                <Button size="sm" variant="outline" disabled={isCreatingResetLink} onClick={() => void handleCreateResetLink(member.email)}>
                  {isCreatingResetLink ? <LoaderCircle className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
                  재설정 링크 만들기
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function ScopeSection({
  title,
  description,
  scope,
  canManage,
  authenticated,
  readinessByProvider,
  connections,
  showManagement = true,
  emptyStateMessage = '아직 연결된 데이터 소스가 없습니다.',
  readOnlyRecordsTitle,
}: {
  title: string
  description: string
  scope: Scope
  canManage: boolean
  authenticated: boolean
  readinessByProvider: Map<string, ConnectorProviderReadiness>
  connections: ConnectorConnectionSummary[]
  showManagement?: boolean
  emptyStateMessage?: string
  readOnlyRecordsTitle?: string
}) {
  const connectionsByProvider = useMemo(
    () => new Map(connections.map((connection) => [connection.provider, connection])),
    [connections],
  )
  const resourceRecords = useMemo(
    () =>
      connections.flatMap((connection) =>
        connection.resources.map((resource) => ({
          connection,
          resource,
        })),
      ),
    [connections],
  )

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="mb-4">
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">{title}</div>
          <div className="mt-1 text-sm text-neutral-500">{description}</div>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {providerDefinitions.map((provider) => (
            <ProviderCard
              key={`${scope}-${provider.key}`}
              provider={provider}
              scope={scope}
              readiness={readinessByProvider.get(provider.key) ?? null}
              connection={connectionsByProvider.get(provider.key) ?? null}
              canManage={canManage}
              authenticated={authenticated}
            />
          ))}
        </div>
      </Card>

      {connections.length === 0 ? (
        <Card className="p-5">
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            {emptyStateMessage}
          </div>
        </Card>
      ) : !showManagement ? (
        readOnlyRecordsTitle ? <ConnectedResourcesList title={readOnlyRecordsTitle} records={resourceRecords} /> : null
      ) : (
        <>
          {connections.map((connection) => (
            <ConnectionManager key={connection.id} connection={connection} canManage={canManage} />
          ))}
          <ResourceTable title={scope === 'workspace' ? '조직에서 가져오는 항목' : '내가 가져오는 항목'} records={resourceRecords} canManage={canManage} />
        </>
      )}
    </div>
  )
}

export function ConnectorsPage() {
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const errorMessage = getErrorMessage(searchParams)
  const [showPersonalConnections, setShowPersonalConnections] = useState(false)
  const loginHref = `/login?return_to=${encodeURIComponent('/connectors')}`
  const isDevelopment = process.env.NODE_ENV !== 'production'

  const authQuery = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => fetchJson<AuthMeResponse>('/api/auth/me'),
  })

  const readinessQuery = useQuery({
    queryKey: ['connectors-readiness'],
    queryFn: () => fetchJson<ConnectorReadinessResponse>('/api/connectors/readiness'),
  })

  const workspaceQuery = useQuery({
    queryKey: ['connectors', 'workspace'],
    queryFn: () => fetchJson<ConnectorListResponse>('/api/connectors?scope=workspace'),
    enabled: authQuery.data?.authenticated === true,
  })

  const personalQuery = useQuery({
    queryKey: ['connectors', 'personal'],
    queryFn: () => fetchJson<ConnectorListResponse>('/api/connectors?scope=personal'),
    enabled: authQuery.data?.authenticated === true,
  })

  const workspaceInvitationsQuery = useQuery({
    queryKey: ['workspace-invitations'],
    queryFn: () => fetchJson<WorkspaceInvitationSummary[]>('/api/workspace/invitations'),
    enabled: authQuery.data?.authenticated === true && authQuery.data?.user?.can_manage_workspace_connectors === true,
  })

  const workspaceMembersQuery = useQuery({
    queryKey: ['workspace-members'],
    queryFn: () => fetchJson<WorkspaceMemberSummary[]>('/api/workspace/members'),
    enabled: authQuery.data?.authenticated === true && authQuery.data?.user?.can_manage_workspace_connectors === true,
  })

  const inviteMutation = useMutation({
    mutationFn: async (payload: { invited_email: string; role: string }) =>
      fetchJson<WorkspaceInvitationCreateResponse>('/api/workspace/invitations', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['workspace-invitations'] })
    },
  })

  const passwordResetLinkMutation = useMutation({
    mutationFn: async (email: string) =>
      fetchJson<PasswordResetLinkCreateResponse>('/api/auth/password/reset-links', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),
  })

  const logoutMutation = useMutation({
    mutationFn: async () =>
      fetchJson<{ ok: boolean }>('/api/auth/logout', {
        method: 'POST',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth-me'] })
      await queryClient.invalidateQueries({ queryKey: ['connectors-readiness'] })
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
    },
  })

  const authenticated = authQuery.data?.authenticated === true
  const user = authQuery.data?.user ?? null
  const canManageWorkspaceConnectors = user?.can_manage_workspace_connectors === true
  const readinessByProvider = useMemo(
    () => new Map((readinessQuery.data?.providers ?? []).map((item) => [item.provider, item])),
    [readinessQuery.data],
  )
  const workspaceConnections = workspaceQuery.data?.items ?? []
  const personalConnections = personalQuery.data?.items ?? []
  const workspaceReady = Array.from(readinessByProvider.values()).some((item) => item.workspace_connection_exists)
  const healthySourceCount = Array.from(readinessByProvider.values()).reduce(
    (sum, item) => sum + item.healthy_source_count,
    0,
  )
  const needsAttentionCount = Array.from(readinessByProvider.values()).reduce(
    (sum, item) => sum + item.needs_attention_count,
    0,
  )
  const workspaceSetupState = Array.from(readinessByProvider.values()).some((item) => item.setup_state === 'attention_required')
    ? 'attention_required'
    : Array.from(readinessByProvider.values()).some((item) => item.setup_state === 'ready')
      ? 'ready'
      : Array.from(readinessByProvider.values()).some((item) => item.setup_state === 'setup_needed')
        ? 'setup_needed'
        : 'not_configured'
  const workspaceResourceRecords = workspaceConnections.flatMap((connection) =>
    connection.resources.map((resource) => ({
      connection,
      resource,
    })),
  )
  const title = !authenticated ? '데이터 소스 설정' : canManageWorkspaceConnectors ? '워크스페이스 데이터 소스' : '워크스페이스 데이터 소스 상태'

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <Link2 className="size-4 text-blue-500" /> 데이터 소스 설정
            </div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">{title}</h1>
            <p className="mt-2 text-sm leading-7 text-neutral-500">
              관리자는 팀의 Google Drive와 Notion을 한 번 연결하고, 구성원은 별도 설정 없이 검색과 문서 탐색에서 같은 지식을 바로 사용합니다.
            </p>
          </div>
          <div className="rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
            {authenticated && user ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                  <UserRound className="size-4 text-blue-500" />
                  {user.name}
                </div>
                <div className="text-sm text-neutral-600 dark:text-neutral-400">{user.email}</div>
                <div className="flex flex-wrap gap-2">
                  <Badge>{canManageWorkspaceConnectors ? '워크스페이스 관리자' : '구성원'}</Badge>
                  {user.current_workspace ? <Badge>{user.current_workspace.name}</Badge> : null}
                  {user.current_workspace_role ? <Badge>{user.current_workspace_role}</Badge> : null}
                  <Badge>최근 로그인 {formatDate(user.last_login_at)}</Badge>
                </div>
                <Button size="sm" variant="outline" onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
                  로그아웃
                </Button>
              </div>
	            ) : (
	              <div className="space-y-3">
	                <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
	                  <Lock className="size-4 text-blue-500" /> 로그인 필요
	                </div>
	                <div className="text-sm text-neutral-500">
	                  헤더, 사이드바, 또는 이 버튼에서 같은 로그인 페이지로 이동할 수 있습니다. 로그인 후에는 원래 보던 연결 흐름으로 바로 돌아옵니다.
	                </div>
	                <Button size="sm" onClick={() => window.location.assign(loginHref)}>
	                  로그인하기
	                </Button>
                {isDevelopment ? (
                  <div className="text-xs text-neutral-400">
                    로컬에서는 로그인한 이메일이 <code>ADMIN_EMAILS</code>에 포함돼야 조직 연결 관리가 열립니다.
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {errorMessage ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
            {errorMessage}
          </div>
        ) : null}

        {!canManageWorkspaceConnectors ? (
          <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-300">
            로그인한 이메일이 관리자 목록에 포함되면 조직 연결 관리가 열립니다.
          </div>
        ) : null}
      </Card>

      {readinessQuery.isLoading ? (
        <Card className="p-5">
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 데이터 소스 준비 상태를 확인하는 중입니다.
          </div>
        </Card>
      ) : null}

      {!readinessQuery.isLoading ? (
        <Card className="p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">워크스페이스 지식 레이어 상태</div>
              <div className="mt-1 text-sm text-neutral-500">
                기본 흐름은 관리자 한 번 연결, 구성원 즉시 활용입니다.
              </div>
            </div>
            <Badge>{formatSetupStateLabel(workspaceSetupState)}</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm dark:border-neutral-800">
              <div className="text-neutral-500">연결된 워크스페이스 소스</div>
              <div className="mt-2 text-2xl font-semibold text-neutral-950 dark:text-neutral-50">{workspaceResourceRecords.length}</div>
            </div>
            <div className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm dark:border-neutral-800">
              <div className="text-neutral-500">정상 상태</div>
              <div className="mt-2 text-2xl font-semibold text-neutral-950 dark:text-neutral-50">{healthySourceCount}</div>
            </div>
            <div className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm dark:border-neutral-800">
              <div className="text-neutral-500">조치 필요</div>
              <div className="mt-2 text-2xl font-semibold text-neutral-950 dark:text-neutral-50">{needsAttentionCount}</div>
            </div>
          </div>
        </Card>
      ) : null}

      {!authenticated ? (
        <ScopeSection
          title="조직 연결"
          description="Google Drive 또는 Notion을 선택하면 로그인 후 바로 해당 데이터 소스 연결 단계로 이어집니다."
          scope="workspace"
          canManage={false}
          authenticated={false}
          readinessByProvider={readinessByProvider}
          connections={workspaceConnections}
          showManagement={false}
          emptyStateMessage="로그인 후 조직 연결을 시작하거나, 조직에서 이미 제공 중인 상태를 확인할 수 있습니다."
        />
      ) : canManageWorkspaceConnectors ? (
        <>
          <WorkspaceAccessPanel
            members={workspaceMembersQuery.data ?? []}
            isLoading={workspaceMembersQuery.isLoading}
            error={workspaceMembersQuery.error instanceof Error ? workspaceMembersQuery.error.message : null}
            createResetError={passwordResetLinkMutation.error instanceof Error ? passwordResetLinkMutation.error.message : null}
            isCreatingResetLink={passwordResetLinkMutation.isPending}
            onCreateResetLink={async (email) => passwordResetLinkMutation.mutateAsync(email)}
          />

          <WorkspaceInvitePanel
            invitations={workspaceInvitationsQuery.data ?? []}
            isLoading={workspaceInvitationsQuery.isLoading}
            error={workspaceInvitationsQuery.error instanceof Error ? workspaceInvitationsQuery.error.message : null}
            createError={inviteMutation.error instanceof Error ? inviteMutation.error.message : null}
            isCreating={inviteMutation.isPending}
            onCreate={async (payload) => inviteMutation.mutateAsync(payload)}
          />

          <ScopeSection
            title="조직 연결"
            description={
              workspaceReady
                ? '조직에서 연결한 공용 문서는 로그인한 모든 사용자가 같은 저장소에서 검색하고 탐색할 수 있습니다.'
                : 'Google Drive 또는 Notion을 한 번 연결해 조직 문서를 공용 저장소로 가져오세요.'
            }
            scope="workspace"
            canManage={true}
            authenticated={true}
            readinessByProvider={readinessByProvider}
            connections={workspaceConnections}
          />

          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">보조 기능: 내 연결</div>
                <div className="mt-1 text-sm text-neutral-500">
                  조직 연결이 우선입니다. 개인 Drive나 Notion은 필요할 때만 별도로 연결하세요.
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={() => setShowPersonalConnections((value) => !value)}>
                {showPersonalConnections ? '내 연결 숨기기' : '내 연결 열기'}
              </Button>
            </div>
          </Card>

          {showPersonalConnections ? (
              <ScopeSection
                title="내 연결"
                description="개인 소스는 보조 경로입니다. 조직 연결이 이미 준비되어 있다면 대부분은 추가 연결 없이 사용할 수 있습니다."
                scope="personal"
                canManage={authenticated}
                authenticated={true}
                readinessByProvider={readinessByProvider}
                connections={personalConnections}
              />
            ) : null}
        </>
      ) : (
        <>
          <Card className="p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <ShieldCheck className="size-4 text-blue-500" /> 조직 연결은 읽기 전용입니다
            </div>
            <div className="text-sm leading-7 text-neutral-500 dark:text-neutral-400">
              현재 워크스페이스에서는 관리자만 조직 Google Drive와 Notion 연결을 만들거나 다시 연결할 수 있습니다. 조직에서 이미 연결한 데이터는 아래에서 그대로 확인할 수 있습니다.
            </div>
          </Card>

          <ScopeSection
            title="조직 연결"
            description={
              workspaceReady
                ? '조직에서 연결한 공용 문서는 로그인한 모든 사용자가 같은 저장소에서 검색하고 탐색할 수 있습니다.'
                : '조직 연결은 워크스페이스 관리자가 준비합니다. 현재 이 화면은 읽기 전용입니다.'
            }
            scope="workspace"
            canManage={false}
            authenticated={true}
            readinessByProvider={readinessByProvider}
            connections={workspaceConnections}
            showManagement={false}
            emptyStateMessage="아직 조직에서 제공 중인 데이터 소스가 없습니다. 연결은 워크스페이스 관리자만 할 수 있습니다."
            readOnlyRecordsTitle={workspaceResourceRecords.length > 0 ? '현재 제공 중인 조직 데이터' : undefined}
          />

          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">보조 기능: 내 연결</div>
                <div className="mt-1 text-sm text-neutral-500">
                  개인 문서가 꼭 필요할 때만 열어 사용하세요. 기본 검색과 문서 탐색은 조직 연결을 기준으로 동작합니다.
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={() => setShowPersonalConnections((value) => !value)}>
                {showPersonalConnections ? '내 연결 숨기기' : '내 연결 열기'}
              </Button>
            </div>
          </Card>

          {showPersonalConnections ? (
            <ScopeSection
              title="내 연결"
              description="개인 소스는 보조 경로입니다. 자주 쓰는 공용 문서는 조직 연결을 우선 사용하세요."
              scope="personal"
              canManage={true}
              authenticated={true}
              readinessByProvider={readinessByProvider}
              connections={personalConnections}
            />
          ) : null}
        </>
      )}

      <Card className="p-5">
        <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">어디서 쓰이나요</div>
        <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
          <div>1. 연결된 데이터 소스는 기존 문서 저장소로 들어와 문서 탐색과 시맨틱 검색에서 바로 보입니다.</div>
          <div>2. 동기화된 문서는 직접 작성한 문서와 같은 방식으로 용어집 후보와 대표 문서 생성에 사용됩니다.</div>
          <div>3. 대부분의 사용자는 연결 화면보다 문서 화면에서 결과를 체감하게 됩니다.</div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          <Link href="/docs" className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400">
            문서 탐색 열기 <ArrowRight className="size-4" />
          </Link>
          <Link href="/search" className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400">
            시맨틱 검색 열기 <ArrowRight className="size-4" />
          </Link>
        </div>
      </Card>
    </div>
  )
}
