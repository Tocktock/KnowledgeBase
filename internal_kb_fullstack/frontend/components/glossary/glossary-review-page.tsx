'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { LoaderCircle, RefreshCcw, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type {
  GlossaryConceptDetailResponse,
  GlossaryConceptListResponse,
  GlossaryConceptSummary,
  JobSummary,
} from '@/lib/types'

async function fetchGlossaryList(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value))
  })
  const response = await fetch(`/api/glossary?${search.toString()}`)
  if (!response.ok) throw new Error('글로서리 목록을 불러오지 못했습니다.')
  return (await response.json()) as GlossaryConceptListResponse
}

async function fetchConcept(id: string) {
  const response = await fetch(`/api/glossary/${id}`)
  if (!response.ok) throw new Error('글로서리 상세를 불러오지 못했습니다.')
  return (await response.json()) as GlossaryConceptDetailResponse
}

async function refreshGlossary(scope: 'full' | 'incremental') {
  const response = await fetch('/api/glossary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope }),
  })
  if (!response.ok) throw new Error('글로서리 리프레시를 시작하지 못했습니다.')
  return (await response.json()) as JobSummary
}

async function generateDraft(id: string, domain: string) {
  const response = await fetch(`/api/glossary/${id}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain: domain || undefined, regenerate: true }),
  })
  if (!response.ok) {
    const body = (await response.json()) as { detail?: string }
    throw new Error(body.detail || '초안 생성에 실패했습니다.')
  }
  return (await response.json()) as GlossaryConceptDetailResponse
}

async function updateConcept(id: string, payload: Record<string, unknown>) {
  const response = await fetch(`/api/glossary/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const body = (await response.json()) as { detail?: string }
    throw new Error(body.detail || '글로서리 상태 변경에 실패했습니다.')
  }
  return (await response.json()) as GlossaryConceptDetailResponse
}

export function GlossaryReviewPage({ initialList }: { initialList: GlossaryConceptListResponse }) {
  const [concepts, setConcepts] = useState<GlossaryConceptSummary[]>(initialList.items)
  const [selectedId, setSelectedId] = useState<string | null>(initialList.items[0]?.id ?? null)
  const [detail, setDetail] = useState<GlossaryConceptDetailResponse | null>(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('suggested')
  const [conceptType, setConceptType] = useState('')
  const [ownerTeam, setOwnerTeam] = useState('')
  const [draftDomain, setDraftDomain] = useState('')
  const [mergeInto, setMergeInto] = useState('')
  const [splitAliases, setSplitAliases] = useState('')
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [acting, setActing] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const selectedConcept = useMemo(
    () => concepts.find((item) => item.id === selectedId) ?? detail?.concept ?? null,
    [concepts, detail, selectedId],
  )

  const loadList = async () => {
    setLoadingList(true)
    setError(null)
    try {
      const data = await fetchGlossaryList({
        query,
        status: statusFilter || undefined,
        concept_type: conceptType || undefined,
        owner_team: ownerTeam || undefined,
        limit: 40,
      })
      setConcepts(data.items)
      if (!data.items.some((item) => item.id === selectedId)) {
        setSelectedId(data.items[0]?.id ?? null)
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '글로서리 목록을 불러오지 못했습니다.')
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    let cancelled = false
    setLoadingDetail(true)
    setError(null)
    fetchConcept(selectedId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((nextError) => {
        if (!cancelled) setError(nextError instanceof Error ? nextError.message : '상세를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const runAction = async (action: () => Promise<GlossaryConceptDetailResponse | JobSummary>, successMessage: string) => {
    setActing(true)
    setError(null)
    setMessage(null)
    try {
      const result = await action()
      if ('concept' in result) {
        setDetail(result)
        setConcepts((current) =>
          current.map((item) => (item.id === result.concept.id ? result.concept : item)),
        )
      }
      setMessage(successMessage)
      await loadList()
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '작업을 수행하지 못했습니다.')
    } finally {
      setActing(false)
    }
  }

  const approvePayload = detail?.concept.generated_document
    ? { action: 'approve', canonical_document_id: detail.concept.generated_document.id }
    : { action: 'approve' }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">글로서리 리뷰 스튜디오</h1>
            <p className="mt-2 text-sm leading-7 text-neutral-500">
              개념 마이닝 결과를 검토하고, 근거를 확인하고, 초안 생성과 승인 상태를 운영합니다.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => void runAction(() => refreshGlossary('incremental'), '증분 리프레시 작업을 등록했습니다.')} disabled={acting}>
              <RefreshCcw className="size-4" /> Incremental refresh
            </Button>
            <Button type="button" onClick={() => void runAction(() => refreshGlossary('full'), '전체 리프레시 작업을 등록했습니다.')} disabled={acting}>
              <Sparkles className="size-4" /> Full refresh
            </Button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_180px_180px_auto]">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="용어 / 별칭 검색" />
          <Input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="status" />
          <Input value={conceptType} onChange={(event) => setConceptType(event.target.value)} placeholder="concept_type" />
          <Input value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="owner_team" />
          <Button type="button" variant="outline" onClick={() => void loadList()} disabled={loadingList}>
            {loadingList ? <LoaderCircle className="size-4 animate-spin" /> : <RefreshCcw className="size-4" />}
            필터 적용
          </Button>
        </div>
      </Card>

      {message ? <Card className="p-4 text-sm text-blue-700 dark:text-blue-300">{message}</Card> : null}
      {error ? <Card className="p-4 text-sm text-red-700 dark:text-red-300">{error}</Card> : null}

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="p-4">
          <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">후보 개념 ({concepts.length})</div>
          <div className="space-y-2">
            {concepts.map((concept) => (
              <button
                key={concept.id}
                type="button"
                onClick={() => setSelectedId(concept.id)}
                className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                  selectedId === concept.id
                    ? 'border-blue-400 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/20'
                    : 'border-neutral-200 hover:border-neutral-300 dark:border-neutral-800 dark:hover:border-neutral-700'
                }`}
              >
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge>{concept.status}</Badge>
                  <Badge>{concept.concept_type}</Badge>
                  <Badge>{concept.support_doc_count} docs</Badge>
                </div>
                <div className="font-medium text-neutral-900 dark:text-neutral-50">{concept.display_term}</div>
                <div className="mt-1 text-xs text-neutral-500">score {concept.confidence_score.toFixed(2)}</div>
                {concept.aliases.length ? (
                  <div className="mt-2 text-xs leading-6 text-neutral-500">{concept.aliases.slice(0, 4).join(', ')}</div>
                ) : null}
              </button>
            ))}
            {concepts.length === 0 ? <div className="rounded-2xl bg-neutral-50 p-4 text-sm text-neutral-500 dark:bg-neutral-900">조건에 맞는 후보가 없습니다.</div> : null}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            {loadingDetail ? (
              <div className="flex items-center gap-2 text-sm text-neutral-500"><LoaderCircle className="size-4 animate-spin" /> 개념 상세를 불러오는 중입니다.</div>
            ) : detail ? (
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge>{detail.concept.status}</Badge>
                      <Badge>{detail.concept.concept_type}</Badge>
                      <Badge>{detail.concept.support_doc_count} docs</Badge>
                      <Badge>{detail.concept.support_chunk_count} chunks</Badge>
                    </div>
                    <h2 className="text-2xl font-semibold text-neutral-950 dark:text-neutral-50">{detail.concept.display_term}</h2>
                    <div className="mt-2 text-sm text-neutral-500">normalized: {detail.concept.normalized_term}</div>
                  </div>
                  <div className="text-right text-sm text-neutral-500">
                    <div>score {detail.concept.confidence_score.toFixed(2)}</div>
                    <div>{detail.concept.owner_team_hint || 'owner team 미지정'}</div>
                  </div>
                </div>

                <div className="rounded-2xl bg-neutral-50 px-4 py-3 text-sm leading-7 text-neutral-600 dark:bg-neutral-900 dark:text-neutral-400">
                  별칭: {detail.concept.aliases.length ? detail.concept.aliases.join(', ') : '없음'}
                </div>

                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <Button type="button" onClick={() => detail && void runAction(() => generateDraft(detail.concept.id, draftDomain), '글로서리 초안을 생성했습니다.')} disabled={acting || !detail}>
                    {acting ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                    Draft 생성
                  </Button>
                  <Button type="button" variant="outline" onClick={() => detail && void runAction(() => updateConcept(detail.concept.id, approvePayload), '개념을 승인했습니다.')} disabled={acting || !detail}>
                    Approve
                  </Button>
                  <Button type="button" variant="outline" onClick={() => detail && void runAction(() => updateConcept(detail.concept.id, { action: 'ignore' }), '개념을 무시 상태로 변경했습니다.')} disabled={acting || !detail}>
                    Ignore
                  </Button>
                  <Button type="button" variant="outline" onClick={() => detail && void runAction(() => updateConcept(detail.concept.id, { action: 'mark_stale' }), '개념을 stale 상태로 변경했습니다.')} disabled={acting || !detail}>
                    Mark stale
                  </Button>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">초안 생성 도메인</div>
                    <Input value={draftDomain} onChange={(event) => setDraftDomain(event.target.value)} placeholder="예: 차량 분류 / 배송 운영" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">생성된 문서</div>
                    {detail.concept.generated_document ? (
                      <Link href={`/docs/${detail.concept.generated_document.slug}`} className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                        /docs/{detail.concept.generated_document.slug}
                      </Link>
                    ) : (
                      <div className="text-sm text-neutral-500">아직 초안이 없습니다.</div>
                    )}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">merge_into_concept_id</div>
                    <Input value={mergeInto} onChange={(event) => setMergeInto(event.target.value)} placeholder="대상 concept UUID" />
                    <Button type="button" variant="outline" onClick={() => detail && void runAction(() => updateConcept(detail.concept.id, { action: 'merge', merge_into_concept_id: mergeInto }), '개념을 병합했습니다.')} disabled={acting || !detail || !mergeInto.trim()}>
                      Merge
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300">split aliases</div>
                    <Input value={splitAliases} onChange={(event) => setSplitAliases(event.target.value)} placeholder="별칭1, 별칭2" />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() =>
                        detail &&
                        void runAction(
                          () =>
                            updateConcept(detail.concept.id, {
                              action: 'split',
                              split_aliases: splitAliases
                                .split(',')
                                .map((item) => item.trim())
                                .filter(Boolean),
                            }),
                          '별칭을 분리했습니다.',
                        )
                      }
                      disabled={acting || !detail || !splitAliases.trim()}
                    >
                      Split
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-sm text-neutral-500">왼쪽에서 개념을 선택하세요.</div>
            )}
          </Card>

          {detail ? (
            <Card className="p-6">
              <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">근거 문서</div>
              <div className="space-y-3">
                {detail.supports.slice(0, 16).map((support) => (
                  <div key={support.id} className="rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge>{support.evidence_kind}</Badge>
                      <Badge>{support.evidence_strength.toFixed(2)}</Badge>
                      <Badge>{support.document_doc_type}</Badge>
                    </div>
                    <Link href={`/docs/${support.document_slug}`} className="font-medium text-neutral-900 hover:text-blue-600 dark:text-neutral-50 dark:hover:text-blue-400">
                      {support.document_title}
                    </Link>
                    <div className="mt-2 text-sm leading-7 text-neutral-600 dark:text-neutral-400">{support.support_text}</div>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}

          {detail?.related_concepts.length ? (
            <Card className="p-6">
              <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">관련 개념 / 중복 후보</div>
              <div className="grid gap-3 md:grid-cols-2">
                {detail.related_concepts.map((concept) => (
                  <Link key={concept.id} href={`/glossary/${concept.slug}`} className="rounded-2xl border border-neutral-200 px-4 py-3 transition hover:border-blue-300 dark:border-neutral-800 dark:hover:border-blue-900">
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge>{concept.status}</Badge>
                      <Badge>{concept.concept_type}</Badge>
                    </div>
                    <div className="font-medium text-neutral-900 dark:text-neutral-50">{concept.display_term}</div>
                    <div className="mt-1 text-xs text-neutral-500">score {concept.confidence_score.toFixed(2)}</div>
                  </Link>
                ))}
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  )
}
