'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, LoaderCircle, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type {
  AuthMeResponse,
  GlossaryConceptRequestCreateRequest,
  GlossaryConceptRequestListResponse,
  GlossaryConceptRequestResponse,
} from '@/lib/types'
import { formatDate, formatStatusLabel, sentence } from '@/lib/utils'

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  const bodyText = await response.text()
  if (!response.ok) {
    try {
      const payload = JSON.parse(bodyText) as { detail?: string }
      throw new Error(payload.detail || '요청을 처리하지 못했습니다.')
    } catch {
      throw new Error(bodyText || '요청을 처리하지 못했습니다.')
    }
  }
  return bodyText ? (JSON.parse(bodyText) as T) : (null as T)
}

function requestStatusLabel(value: string) {
  if (value === 'created') return '요청 등록'
  if (value === 'updated_existing') return '기존 후보에 추가'
  if (value === 'already_exists') return '이미 존재함'
  return value
}

function formatValidationStateLabel(value: string) {
  if (value === 'needs_update') return '업데이트 필요'
  if (value === 'missing_draft') return '초안 필요'
  if (value === 'stale_evidence') return '근거 재검토'
  if (value === 'new_term') return '신규 용어'
  return value
}

export function GlossaryRequestPanel() {
  const queryClient = useQueryClient()
  const authQuery = useQuery({
    queryKey: ['auth-me', 'glossary-request-panel'],
    queryFn: () => fetchJson<AuthMeResponse>('/api/auth/me'),
  })
  const [term, setTerm] = useState('')
  const [aliases, setAliases] = useState('')
  const [ownerTeamHint, setOwnerTeamHint] = useState('')
  const [requestNote, setRequestNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GlossaryConceptRequestResponse | null>(null)

  const auth = authQuery.data
  const authenticated = auth?.authenticated === true
  const hasWorkspace = auth?.user?.current_workspace != null
  const isAdmin = auth?.user?.can_manage_workspace_connectors === true
  const requestListQuery = useQuery({
    queryKey: ['glossary-my-requests'],
    enabled: authenticated && hasWorkspace,
    queryFn: () => fetchJson<GlossaryConceptRequestListResponse>('/api/glossary/requests?limit=20'),
  })

  const submitRequest = async () => {
    setSubmitting(true)
    setError(null)
    setMessage(null)
    try {
      const payload: GlossaryConceptRequestCreateRequest = {
        term,
        aliases: aliases
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        request_note: requestNote.trim() || undefined,
        owner_team_hint: ownerTeamHint.trim() || undefined,
      }
      const response = await fetchJson<GlossaryConceptRequestResponse>('/api/glossary/requests', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setResult(response)
      setMessage(response.message)
      await queryClient.invalidateQueries({ queryKey: ['glossary-my-requests'] })
      if (response.request_status === 'created') {
        setTerm('')
        setAliases('')
        setOwnerTeamHint('')
        setRequestNote('')
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '요청을 등록하지 못했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 flex flex-wrap gap-2">
          <Badge>새 핵심 개념 요청</Badge>
          {authenticated && hasWorkspace ? <Badge>{auth?.user?.current_workspace?.name}</Badge> : null}
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">
          요청은 여기서 받고, 승인은 관리자가 진행합니다.
        </h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">
          없는 용어를 요청하고 내가 올린 요청의 현재 상태를 확인할 수 있습니다. 최종 승인과 대표 문서 결정은 지식 검수에서 진행됩니다.
        </p>
      </div>

      <Card className="p-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">
              새 요청 등록
            </h2>
            <p className="mt-2 text-sm leading-7 text-neutral-500">
              용어, 별칭, 요청 배경을 남기면 지식 검수 큐에 새 후보로 등록됩니다.
            </p>
          </div>
          {isAdmin ? (
            <Link
              href="/glossary/review"
              className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-300 dark:hover:bg-blue-950/40"
            >
              지식 검수 열기 <ArrowRight className="size-4" />
            </Link>
          ) : null}
        </div>

        {authQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 요청 권한을 확인하는 중입니다.
          </div>
        ) : !authenticated ? (
          <div className="space-y-3 rounded-2xl border border-neutral-200 px-4 py-4 text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
            <div>로그인하면 워크스페이스 핵심 개념 요청을 등록하고 내 요청 현황을 확인할 수 있습니다.</div>
            <div>
              <Button type="button" onClick={() => window.location.assign('/login?return_to=%2Fglossary%2Frequests')}>
                로그인하고 요청하기
              </Button>
            </div>
          </div>
        ) : !hasWorkspace ? (
          <div className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm leading-7 text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
            현재 계정에는 활성 워크스페이스가 없습니다. 워크스페이스 초대를 수락한 뒤 핵심 개념 요청을 등록할 수 있습니다.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
              <div className="space-y-2">
                <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">용어</div>
                <Input value={term} onChange={(event) => setTerm(event.target.value)} placeholder="예: 센디 차량 등급" />
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">소유 그룹</div>
                <Input value={ownerTeamHint} onChange={(event) => setOwnerTeamHint(event.target.value)} placeholder="예: product / operations" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">별칭</div>
              <Input value={aliases} onChange={(event) => setAliases(event.target.value)} placeholder="예: 센디 차량, 센디 카테고리" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">요청 배경</div>
              <Textarea
                value={requestNote}
                onChange={(event) => setRequestNote(event.target.value)}
                placeholder="이 용어가 어디에서 쓰이고, 왜 핵심 개념으로 관리되어야 하는지 적어 주세요."
                className="min-h-[132px]"
              />
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" onClick={() => void submitRequest()} disabled={submitting || !term.trim()}>
                {submitting ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                요청 등록
              </Button>
              <div className="text-xs text-neutral-500">
                요청은 즉시 공개되지 않습니다. 관리자가 지식 검수에서 초안을 만들고 승인해야 Concepts 목록에 나타납니다.
              </div>
            </div>
          </div>
        )}

        {message ? (
          <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-300">
            {message}
            {result ? (
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge>{requestStatusLabel(result.request_status)}</Badge>
                <Badge>{result.concept.display_term}</Badge>
                {result.concept.status === 'approved' ? (
                  <Link href={`/glossary/${result.concept.slug}`} className="text-sm font-medium underline underline-offset-4">
                    승인된 개념 열기
                  </Link>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
            {error}
          </div>
        ) : null}
      </Card>

      <Card className="p-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">내 요청 현황</h2>
            <p className="mt-2 text-sm leading-7 text-neutral-500">
              내가 등록한 용어 요청이 검수 단계에서 어디까지 진행됐는지 확인할 수 있습니다.
            </p>
          </div>
          {isAdmin ? (
            <Link href="/glossary/review" className="text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
              지식 검수 바로가기
            </Link>
          ) : null}
        </div>

        {!authenticated ? (
          <div className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
            로그인 후 내 요청 현황을 확인할 수 있습니다.
          </div>
        ) : !hasWorkspace ? (
          <div className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
            워크스페이스 초대 수락이 완료되면 요청 현황이 이 페이지에 표시됩니다.
          </div>
        ) : requestListQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <LoaderCircle className="size-4 animate-spin" /> 요청 현황을 불러오는 중입니다.
          </div>
        ) : requestListQuery.isError ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
            {requestListQuery.error instanceof Error ? requestListQuery.error.message : '요청 현황을 불러오지 못했습니다.'}
          </div>
        ) : requestListQuery.data && requestListQuery.data.items.length > 0 ? (
          <div className="space-y-3">
            {requestListQuery.data.items.map((item) => (
              <div key={item.concept.id} className="rounded-2xl border border-neutral-200 px-4 py-4 dark:border-neutral-800">
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge>{formatStatusLabel(item.concept.status)}</Badge>
                  <Badge>{formatValidationStateLabel(item.concept.validation_state)}</Badge>
                  <Badge>내 요청 {item.request_count}건</Badge>
                </div>
                <div className="break-words text-lg font-semibold text-neutral-950 dark:text-neutral-50">{item.concept.display_term}</div>
                <div className="mt-1 text-sm text-neutral-500">
                  최근 요청 {formatDate(item.latest_request.requested_at ?? null)}
                </div>
                {item.latest_request.request_note ? (
                  <div className="mt-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
                    {sentence(item.latest_request.request_note, 220)}
                  </div>
                ) : null}
                <div className="mt-4 flex flex-wrap gap-3 text-sm">
                  {item.concept.status === 'approved' ? (
                    <Link href={`/glossary/${item.concept.slug}`} className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                      승인된 개념 열기
                    </Link>
                  ) : (
                    <div className="text-neutral-500 dark:text-neutral-400">현재 검수 큐에서 상태를 관리하고 있습니다.</div>
                  )}
                  {isAdmin ? (
                    <Link href="/glossary/review" className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                      검수 화면 열기
                    </Link>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-6 text-sm text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
            아직 등록한 핵심 개념 요청이 없습니다.
          </div>
        )}
      </Card>
    </div>
  )
}
