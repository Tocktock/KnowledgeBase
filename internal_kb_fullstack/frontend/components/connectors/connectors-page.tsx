'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FolderOpen,
  HardDrive,
  Link2,
  LoaderCircle,
  Lock,
  RefreshCcw,
  ShieldCheck,
  Trash2,
  UserRound,
} from 'lucide-react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
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
  ConnectorReadinessResponse,
  ConnectorSourceItemSummary,
  ConnectorTargetSummary,
} from '@/lib/types'
import {
  formatConnectorItemStatusLabel,
  formatConnectorScopeLabel,
  formatConnectorStatusLabel,
  formatConnectorSyncModeLabel,
  formatConnectorTargetTypeLabel,
  formatDate,
  formatStatusLabel,
} from '@/lib/utils'

type BrowseKind = 'folder' | 'shared_drive'
type SyncMode = 'manual' | 'auto'

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
  if (authError === 'login_unavailable') return '관리자가 Google 연결 기능을 아직 준비하지 않았습니다.'
  if (connectorError === 'session_missing') return '연결을 시작하기 전에 다시 로그인해 주세요.'
  if (connectorError === 'org_admin_required') return '조직 연결은 관리자만 시작할 수 있습니다.'
  if (connectorError === 'start_failed') return 'Google Drive 연결 시작에 실패했습니다.'
  if (connectorError === 'callback_failed') return 'Google Drive 연결 콜백 처리에 실패했습니다.'
  return null
}

function SyncSummary({ target }: { target: ConnectorTargetSummary }) {
  const summary = target.last_sync_summary || {}
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

function TargetRow({
  connectionId,
  target,
  canManage,
}: {
  connectionId: string
  target: ConnectorTargetSummary
  canManage: boolean
}) {
  const queryClient = useQueryClient()
  const [syncMode, setSyncMode] = useState<SyncMode>(target.sync_mode === 'auto' ? 'auto' : 'manual')
  const [intervalMinutes, setIntervalMinutes] = useState<number>(target.sync_interval_minutes ?? 60)

  const updateMutation = useMutation({
    mutationFn: async (payload: Partial<Pick<ConnectorTargetSummary, 'sync_mode' | 'sync_interval_minutes' | 'status' | 'include_subfolders'>>) =>
      fetchJson<ConnectorTargetSummary>(`/api/connectors/${connectionId}/targets/${target.id}`, {
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
      fetchJson<{ title: string }>(`/api/connectors/${connectionId}/targets/${target.id}/sync`, {
        method: 'POST',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
      await queryClient.invalidateQueries({ queryKey: ['connector-items', connectionId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () =>
      fetchJson<void>(`/api/connectors/${connectionId}/targets/${target.id}`, {
        method: 'DELETE',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['connectors'] })
    },
  })

  return (
    <div className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-neutral-950 dark:text-neutral-50">
            <span>{target.name}</span>
            <Badge>{formatConnectorTargetTypeLabel(target.target_type)}</Badge>
            <Badge>{formatStatusLabel(target.status)}</Badge>
            <Badge>{formatConnectorSyncModeLabel(target.sync_mode)}</Badge>
            {target.include_subfolders ? <Badge>하위 폴더 포함</Badge> : null}
          </div>
          <div className="mt-2 text-xs text-neutral-400">
            최근 시작 {formatDate(target.last_sync_started_at)} · 최근 완료 {formatDate(target.last_sync_completed_at)}
          </div>
          {target.next_auto_sync_at ? (
            <div className="mt-1 text-xs text-neutral-400">다음 자동 동기화 {formatDate(target.next_auto_sync_at)}</div>
          ) : null}
        </div>
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
      </div>

      <div className="grid gap-3 md:grid-cols-[180px_180px_1fr]">
        <label className="space-y-2 text-sm">
          <div className="font-medium text-neutral-700 dark:text-neutral-300">동기화 방식</div>
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
        </label>

        <label className="space-y-2 text-sm">
          <div className="font-medium text-neutral-700 dark:text-neutral-300">자동 주기</div>
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
        </label>

        <div className="space-y-2 text-sm">
          <div className="font-medium text-neutral-700 dark:text-neutral-300">최근 결과</div>
          <SyncSummary target={target} />
        </div>
      </div>

      {updateMutation.error ? (
        <div className="mt-3 text-sm text-red-600 dark:text-red-400">
          {updateMutation.error instanceof Error ? updateMutation.error.message : '대상 설정을 바꾸지 못했습니다.'}
        </div>
      ) : null}
      {syncMutation.error ? (
        <div className="mt-3 text-sm text-red-600 dark:text-red-400">
          {syncMutation.error instanceof Error ? syncMutation.error.message : '동기화를 요청하지 못했습니다.'}
        </div>
      ) : null}
    </div>
  )
}

function ConnectionCard({
  connection,
  canManage,
}: {
  connection: ConnectorConnectionSummary
  canManage: boolean
}) {
  const queryClient = useQueryClient()
  const [browseKind, setBrowseKind] = useState<BrowseKind>('folder')
  const [browseParentId, setBrowseParentId] = useState<string | null>(null)
  const [browseDriveId, setBrowseDriveId] = useState<string | null>(null)
  const [browseHistory, setBrowseHistory] = useState<Array<{ parentId: string | null; driveId: string | null }>>([])
  const [browseItems, setBrowseItems] = useState<ConnectorBrowseItem[]>([])
  const [browseLoading, setBrowseLoading] = useState(false)
  const [browseError, setBrowseError] = useState<string | null>(null)
  const [targetType, setTargetType] = useState<BrowseKind>('folder')
  const [externalId, setExternalId] = useState('')
  const [targetName, setTargetName] = useState('')
  const [includeSubfolders, setIncludeSubfolders] = useState(true)
  const [syncMode, setSyncMode] = useState<SyncMode>(connection.owner_scope === 'shared' ? 'auto' : 'manual')
  const [syncIntervalMinutes, setSyncIntervalMinutes] = useState(60)
  const [showItems, setShowItems] = useState(false)

  const itemsQuery = useQuery({
    queryKey: ['connector-items', connection.id],
    queryFn: () => fetchJson<ConnectorSourceItemSummary[]>(`/api/connectors/${connection.id}/items`),
    enabled: showItems,
  })

  const createTargetMutation = useMutation({
    mutationFn: async () =>
      fetchJson<ConnectorTargetSummary>(`/api/connectors/${connection.id}/targets`, {
        method: 'POST',
        body: JSON.stringify({
          target_type: targetType,
          external_id: externalId,
          name: targetName,
          include_subfolders: includeSubfolders,
          sync_mode: syncMode,
          sync_interval_minutes: syncMode === 'auto' ? syncIntervalMinutes : null,
        }),
      }),
    onSuccess: async () => {
      setExternalId('')
      setTargetName('')
      setBrowseItems([])
      setBrowseParentId(null)
      setBrowseDriveId(null)
      setBrowseHistory([])
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

  async function loadBrowse(nextKind: BrowseKind, options?: { parentId?: string | null; driveId?: string | null }) {
    setBrowseLoading(true)
    setBrowseError(null)
    try {
      const search = new URLSearchParams({ kind: nextKind })
      if (options?.parentId) search.set('parent_id', options.parentId)
      if (options?.driveId) search.set('drive_id', options.driveId)
      const payload = await fetchJson<ConnectorBrowseResponse>(`/api/connectors/${connection.id}/browse?${search.toString()}`)
      setBrowseKind(nextKind)
      setBrowseParentId(options?.parentId ?? null)
      setBrowseDriveId(options?.driveId ?? null)
      setBrowseItems(payload.items)
    } catch (error) {
      setBrowseError(error instanceof Error ? error.message : '연결 대상을 불러오지 못했습니다.')
    } finally {
      setBrowseLoading(false)
    }
  }

  const visibleItems = useMemo(() => itemsQuery.data?.slice(0, 8) ?? [], [itemsQuery.data])

  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-lg font-semibold text-neutral-950 dark:text-neutral-50">{connection.display_name}</div>
            <Badge>{formatConnectorScopeLabel(connection.owner_scope)}</Badge>
            <Badge>{formatConnectorStatusLabel(connection.status)}</Badge>
          </div>
          <div className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
            {connection.account_email || 'Google 계정 이메일 없음'}
          </div>
          <div className="mt-1 text-xs text-neutral-400">
            최근 검증 {formatDate(connection.last_validated_at)} · 연결 생성 {formatDate(connection.created_at)}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {connection.account_email ? (
            <Badge>{connection.account_email}</Badge>
          ) : null}
          <Badge>{connection.granted_scopes.includes('https://www.googleapis.com/auth/drive.readonly') ? 'Drive 읽기 권한' : '권한 확인 필요'}</Badge>
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
      </div>

      <div className="space-y-3">
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">동기화 대상</div>
        {connection.targets.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-5 text-sm text-neutral-500 dark:border-neutral-700">
            아직 등록된 폴더나 공유 드라이브가 없습니다.
          </div>
        ) : (
          connection.targets.map((target) => (
            <TargetRow key={target.id} connectionId={connection.id} target={target} canManage={canManage} />
          ))
        )}
      </div>

      <div className="mt-5 rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">새 대상 등록</div>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!canManage || browseLoading}
              onClick={() => {
                setTargetType('folder')
                loadBrowse('folder')
              }}
            >
              <FolderOpen className="size-4" /> 폴더 둘러보기
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={!canManage || browseLoading}
              onClick={() => {
                setTargetType('shared_drive')
                loadBrowse('shared_drive')
              }}
            >
              <HardDrive className="size-4" /> 공유 드라이브 보기
            </Button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-2 text-sm">
            <div className="font-medium text-neutral-700 dark:text-neutral-300">대상 종류</div>
            <select
              className={selectClassName}
              value={targetType}
              onChange={(event) => setTargetType(event.target.value as BrowseKind)}
              disabled={!canManage}
            >
              <option value="folder">폴더</option>
              <option value="shared_drive">공유 드라이브</option>
            </select>
          </label>
          <label className="space-y-2 text-sm">
            <div className="font-medium text-neutral-700 dark:text-neutral-300">대상 이름</div>
            <Input value={targetName} onChange={(event) => setTargetName(event.target.value)} disabled={!canManage} />
          </label>
          <label className="space-y-2 text-sm">
            <div className="font-medium text-neutral-700 dark:text-neutral-300">외부 ID</div>
            <Input value={externalId} onChange={(event) => setExternalId(event.target.value)} disabled={!canManage} />
          </label>
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

        <label className="mt-3 flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
          <input
            type="checkbox"
            checked={includeSubfolders}
            disabled={!canManage}
            onChange={(event) => setIncludeSubfolders(event.target.checked)}
          />
          하위 폴더까지 포함
        </label>

        {browseItems.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">
                {browseKind === 'shared_drive' ? '공유 드라이브 선택' : '폴더 선택'}
              </div>
              {browseKind === 'folder' && browseHistory.length > 0 ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    const previous = browseHistory[browseHistory.length - 1]
                    setBrowseHistory((items) => items.slice(0, -1))
                    loadBrowse('folder', previous)
                  }}
                >
                  이전 폴더
                </Button>
              ) : null}
            </div>
            <div className="space-y-2">
              {browseItems.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800"
                >
                  <div>
                    <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50">{item.name}</div>
                    <div className="text-xs text-neutral-400">{item.id}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setTargetType(item.kind as BrowseKind)
                        setExternalId(item.id)
                        setTargetName(item.name)
                      }}
                    >
                      선택
                    </Button>
                    {browseKind === 'folder' ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setBrowseHistory((items) => [...items, { parentId: browseParentId, driveId: browseDriveId }])
                          loadBrowse('folder', { parentId: item.id, driveId: item.drive_id ?? browseDriveId })
                        }}
                      >
                        열기 <ArrowRight className="size-4" />
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {browseLoading ? (
          <div className="mt-3 flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 연결 대상을 불러오는 중입니다.
          </div>
        ) : null}
        {browseError ? <div className="mt-3 text-sm text-red-600 dark:text-red-400">{browseError}</div> : null}
        {createTargetMutation.error ? (
          <div className="mt-3 text-sm text-red-600 dark:text-red-400">
            {createTargetMutation.error instanceof Error ? createTargetMutation.error.message : '대상을 등록하지 못했습니다.'}
          </div>
        ) : null}

        <div className="mt-4">
          <Button
            disabled={!canManage || !externalId.trim() || !targetName.trim() || createTargetMutation.isPending}
            onClick={() => createTargetMutation.mutate()}
          >
            {createTargetMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
            대상 등록
          </Button>
        </div>
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
          <div className="text-sm text-neutral-500">최근 가져온 파일 상태를 확인하려면 항목 보기를 누르세요.</div>
        )}
      </div>
    </Card>
  )
}

export function ConnectorsPage() {
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const errorMessage = getErrorMessage(searchParams)

  const authQuery = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => fetchJson<AuthMeResponse>('/api/auth/me'),
  })

  const readinessQuery = useQuery({
    queryKey: ['connectors-readiness'],
    queryFn: () => fetchJson<ConnectorReadinessResponse>('/api/connectors/readiness'),
  })

  const sharedQuery = useQuery({
    queryKey: ['connectors', 'shared'],
    queryFn: () => fetchJson<ConnectorListResponse>('/api/connectors?scope=shared'),
    enabled: authQuery.data?.authenticated === true,
  })

  const userQuery = useQuery({
    queryKey: ['connectors', 'user'],
    queryFn: () => fetchJson<ConnectorListResponse>('/api/connectors?scope=user'),
    enabled: authQuery.data?.authenticated === true,
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
  const isAdmin = user?.is_admin === true
  const readiness = readinessQuery.data ?? null
  const organizationConnections = sharedQuery.data?.items ?? []
  const userConnections = userQuery.data?.items ?? []
  const oauthConfigured = readiness?.oauth_configured === true
  const organizationConnectionExists = readiness?.organization_connection_exists === true
  const organizationConnectionStatus = organizationConnections[0]?.status ?? readiness?.organization_connection_status ?? null
  const organizationNeedsReauth = organizationConnectionStatus === 'needs_reauth'
  const personalNeedsReauth = userConnections.some((connection) => connection.status === 'needs_reauth')
  const organizationConnectHref = `/api/connectors/google-drive/oauth/start?scope=shared&return_to=${encodeURIComponent('/connectors')}`
  const personalConnectHref = `/api/connectors/google-drive/oauth/start?scope=user&return_to=${encodeURIComponent('/connectors')}`

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <Link2 className="size-4 text-blue-500" /> 외부 문서 연결
            </div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">연결 소스</h1>
            <p className="mt-2 text-sm leading-7 text-neutral-500">
              조직 관리자는 팀 문서를 한 번 연결하고, 구성원은 준비된 문서를 바로 검색하고 탐색할 수 있습니다. 개인 Drive 연결도 계속 지원합니다.
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
                  <Badge>{user.is_admin ? '관리자' : '구성원'}</Badge>
                  <Badge>최근 로그인 {formatDate(user.last_login_at)}</Badge>
                </div>
                <Button size="sm" variant="outline" onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
                  로그아웃
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                  <Lock className="size-4 text-blue-500" /> 로그인 전
                </div>
                <div className="text-sm text-neutral-500">버튼을 누르면 Google 로그인과 Drive 연결이 한 흐름으로 이어집니다.</div>
              </div>
            )}
          </div>
        </div>

        {errorMessage ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
            {errorMessage}
          </div>
          ) : null}
      </Card>

      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <ShieldCheck className="size-4 text-blue-500" /> 조직 연결
            </div>
            <div className="mt-1 text-sm text-neutral-500">
              관리자가 팀 공용 Drive를 한 번 연결하면, 로그인한 모든 사용자가 상태를 보고 같은 문서를 활용할 수 있습니다.
            </div>
          </div>
          {!oauthConfigured && readinessQuery.isSuccess ? (
            <Badge>관리자 준비 필요</Badge>
          ) : organizationConnectionExists ? (
            isAdmin && organizationNeedsReauth ? (
              <Button size="sm" onClick={() => window.location.assign(organizationConnectHref)}>
                조직 Google Drive 다시 연결
              </Button>
            ) : (
              <Badge>{organizationNeedsReauth ? '재연결 필요' : '조직 문서 연결 완료'}</Badge>
            )
          ) : authenticated && !isAdmin ? (
            <Badge>조직 관리자 준비 중</Badge>
          ) : (
            <Button size="sm" disabled={!oauthConfigured} onClick={() => window.location.assign(organizationConnectHref)}>
              조직 Google Drive 연결
            </Button>
          )}
        </div>

        {readinessQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 조직 연결 준비 상태를 확인하는 중입니다.
          </div>
        ) : !oauthConfigured ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            관리자가 Google OAuth를 배포에 설정하면 이 영역에서 조직 Google Drive를 연결할 수 있습니다.
          </div>
        ) : organizationConnectionExists ? (
          !authenticated ? (
            <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
              조직 문서 연결이 준비되어 있습니다. 로그인하면 연결 상태와 동기화 결과를 볼 수 있습니다.
            </div>
          ) : sharedQuery.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-neutral-500">
              <LoaderCircle className="size-4 animate-spin" /> 조직 연결 목록을 불러오는 중입니다.
            </div>
          ) : sharedQuery.error ? (
            <div className="text-sm text-red-600 dark:text-red-400">
              {sharedQuery.error instanceof Error ? sharedQuery.error.message : '조직 연결을 불러오지 못했습니다.'}
            </div>
          ) : organizationConnections.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
              조직 연결 정보가 아직 동기화되지 않았습니다. 잠시 후 다시 확인해 주세요.
            </div>
          ) : (
            <div className="space-y-4">
              {organizationConnections.map((connection) => (
                <ConnectionCard key={connection.id} connection={connection} canManage={isAdmin} />
              ))}
            </div>
          )
        ) : authenticated && isAdmin ? (
          <div className="rounded-2xl border border-dashed border-blue-300 bg-blue-50/70 px-4 py-8 text-sm text-blue-900 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-100">
            아직 조직 문서 연결이 없습니다. 관리자 계정으로 Google Drive를 한 번 연결하면 팀 폴더와 공유 드라이브를 바로 동기화할 수 있습니다.
          </div>
        ) : authenticated ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            아직 조직 관리자가 팀 문서를 연결하지 않았습니다. 준비가 끝나면 별도 설정 없이 바로 같은 문서를 사용할 수 있습니다.
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            조직 문서 연결은 관리자 한 번의 승인으로 준비됩니다. 관리자라면 위 버튼으로 바로 시작할 수 있습니다.
          </div>
        )}
      </Card>

      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <UserRound className="size-4 text-blue-500" /> 내 연결
            </div>
            <div className="mt-1 text-sm text-neutral-500">
              개인 Drive는 필요할 때만 따로 연결합니다. 조직 문서 연결이 먼저 준비되어 있다면 대부분은 추가 연결 없이 사용할 수 있습니다.
            </div>
          </div>
          {oauthConfigured ? (
            <Button size="sm" onClick={() => window.location.assign(personalConnectHref)}>
              {personalNeedsReauth ? '내 Google Drive 다시 연결' : '내 Google Drive 연결'}
            </Button>
          ) : (
            <Badge>관리자 준비 후 사용 가능</Badge>
          )}
        </div>

        {!oauthConfigured ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            조직 연결 기능이 준비되면 개인 Drive도 같은 버튼 흐름으로 연결할 수 있습니다.
          </div>
        ) : !authenticated ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            버튼을 누르면 Google 로그인 후 바로 내 Drive 연결 단계로 이어집니다.
          </div>
        ) : userQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 내 연결 목록을 불러오는 중입니다.
          </div>
        ) : userQuery.error ? (
          <div className="text-sm text-red-600 dark:text-red-400">
            {userQuery.error instanceof Error ? userQuery.error.message : '내 연결을 불러오지 못했습니다.'}
          </div>
        ) : userConnections.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 dark:border-neutral-700">
            아직 내 Google Drive 연결이 없습니다. 개인 문서를 따로 가져오고 싶을 때만 연결하면 됩니다.
          </div>
        ) : (
          <div className="space-y-4">
            {userConnections.map((connection) => (
              <ConnectionCard key={connection.id} connection={connection} canManage />
            ))}
          </div>
        )}
      </Card>

      <Card className="p-5">
        <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">동작 방식</div>
        <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
          <div>1. 조직 관리자는 조직 Google Drive를 한 번 연결하고, 공유 드라이브나 팀 폴더를 동기화 대상으로 등록합니다.</div>
          <div>2. 조직 연결은 기본으로 자동 동기화되며, 개인 연결은 필요할 때만 수동으로 추가할 수 있습니다.</div>
          <div>3. 동기화된 문서는 기존 문서 저장소로 들어가 검색, 문서 탐색, 용어집 생성 흐름에 함께 포함됩니다.</div>
        </div>
      </Card>
    </div>
  )
}
