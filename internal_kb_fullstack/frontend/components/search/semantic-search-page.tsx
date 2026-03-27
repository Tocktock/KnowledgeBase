'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Brain, Search, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { FormEvent, useState } from 'react'

import { TrustBadges } from '@/components/trust/trust-badges'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { AuthMeResponse, SearchExplainResponse, SearchRequest, SearchResponse } from '@/lib/types'
import {
  formatEvidenceKindLabel,
  formatDate,
  formatStatusLabel,
} from '@/lib/utils'

async function fetchAuthMe() {
  const response = await fetch('/api/auth/me', { cache: 'no-store' })
  if (!response.ok) throw new Error('로그인 상태를 불러오지 못했습니다.')
  return (await response.json()) as AuthMeResponse
}

async function semanticSearch(payload: SearchRequest) {
  const [searchResponse, explainResponse] = await Promise.all([
    fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
    fetch('/api/search/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  ])
  if (!searchResponse.ok) throw new Error('검색에 실패했습니다.')
  if (!explainResponse.ok) throw new Error('검색 설명을 불러오지 못했습니다.')
  return {
    search: (await searchResponse.json()) as SearchResponse,
    explain: (await explainResponse.json()) as SearchExplainResponse,
  }
}

export function SemanticSearchPage() {
  const [query, setQuery] = useState('')
  const [docType, setDocType] = useState('')
  const [ownerTeam, setOwnerTeam] = useState('')

  const authQuery = useQuery({
    queryKey: ['auth-me', 'search-page'],
    queryFn: fetchAuthMe,
  })

  const mutation = useMutation({ mutationFn: semanticSearch })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    mutation.mutate({
      query,
      limit: 10,
      doc_type: docType || undefined,
      owner_team: ownerTeam || undefined,
    })
  }

  const hits = mutation.data?.search.hits ?? []
  const explain = mutation.data?.explain

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden p-6">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          <Brain className="size-4 text-blue-500" /> 워크스페이스 검색
        </div>
        <div className="mb-4 text-sm leading-7 text-neutral-500 dark:text-neutral-400">
          연결된 데이터 소스와 내부 문서를 함께 검색합니다. 기본 화면은 바로 판단에 도움이 되는 결과를 보여주고,
          점수와 해석 로직은 필요할 때만 펼쳐볼 수 있습니다.
        </div>
        <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_200px_200px_auto]">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 차량 분류, 배송 운영 정책, 고객 응대 기준" />
          <Input value={docType} onChange={(event) => setDocType(event.target.value)} placeholder="문서 타입 예: knowledge, runbook" />
          <Input value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="소유 그룹 예: platform, product" />
          <Button type="submit" className="w-full">
            <Search className="size-4" /> 검색
          </Button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-neutral-500">
          <Badge>연결된 팀 지식 검색</Badge>
          <Badge>출처와 최신성 함께 표시</Badge>
          <Badge>개념 기반 보강</Badge>
          <Badge>필요할 때만 상세 근거 보기</Badge>
        </div>
      </Card>

      {mutation.isError ? (
        <Card className="p-5 text-sm text-red-600 dark:text-red-400">{mutation.error instanceof Error ? mutation.error.message : '오류가 발생했습니다.'}</Card>
      ) : null}

      {explain ? (
        <Card className="p-5">
          <details className="group">
            <summary className="cursor-pointer list-none text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              검색이 이 질의를 해석한 방식 보기
            </summary>
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge>검색 기준어 {explain.normalized_query}</Badge>
                {explain.resolved_concept_term ? <Badge>해석된 개념 {explain.resolved_concept_term}</Badge> : <Badge>개념 해석 없음</Badge>}
                {explain.resolved_concept_status ? <Badge>{formatStatusLabel(explain.resolved_concept_status)}</Badge> : null}
                {explain.canonical_document_slug ? <Badge>대표 문서 /docs/{explain.canonical_document_slug}</Badge> : null}
                {explain.weak_grounding ? <Badge className="border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">근거 보강 필요</Badge> : null}
              </div>
              {explain.notes?.length ? (
                <div className="space-y-2 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
                  {explain.notes.map((note) => (
                    <div key={note} className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                      {note}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-neutral-500">개념 후보와 근거 문서를 함께 반영해 결과를 정렬했습니다.</div>
              )}
            </div>
          </details>
        </Card>
      ) : null}

      <div className="space-y-4">
        {mutation.isPending ? (
          Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} className="animate-pulse p-5">
              <div className="mb-3 h-5 w-2/3 rounded bg-neutral-200 dark:bg-neutral-800" />
              <div className="mb-2 h-4 w-full rounded bg-neutral-100 dark:bg-neutral-900" />
              <div className="h-4 w-5/6 rounded bg-neutral-100 dark:bg-neutral-900" />
            </Card>
          ))
        ) : hits.length ? (
          hits.map((hit) => (
            <Card key={hit.chunk_id} className="p-5">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <Link href={`/docs/${hit.document_slug}`} className="text-lg font-semibold text-neutral-950 hover:text-blue-600 dark:text-neutral-50 dark:hover:text-blue-400">
                    {hit.document_title}
                  </Link>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-neutral-400">
                    {hit.matched_concept_term ? <Badge>관련 개념 {hit.matched_concept_term}</Badge> : null}
                    {hit.evidence_kind ? <Badge>{formatEvidenceKindLabel(hit.evidence_kind)}</Badge> : null}
                    {hit.section_title ? <Badge>{hit.section_title}</Badge> : null}
                    {hit.heading_path.map((item) => (
                      <Badge key={item}>{item}</Badge>
                    ))}
                  </div>
                </div>
                <div className="text-right text-xs text-neutral-400">최근 동기화 {formatDate(hit.trust.last_synced_at)}</div>
              </div>
              <TrustBadges trust={hit.trust} showSourceLink={Boolean(hit.trust.source_url)} />
              <p className="text-sm leading-7 text-neutral-600 dark:text-neutral-400">{hit.content_text}</p>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm text-neutral-500 dark:text-neutral-400">
                  {hit.matched_concept_term
                    ? '이 개념을 이해하는 데 바로 도움이 되는 근거 문장입니다.'
                    : '문서를 열어 전체 맥락과 원문을 확인할 수 있습니다.'}
                </div>
                <Link href={`/docs/${hit.document_slug}`} className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                  문서 열기
                  <ArrowUpRight className="size-4" />
                </Link>
              </div>
              <details className="mt-4 rounded-2xl border border-neutral-200 px-4 py-3 text-sm dark:border-neutral-800">
                <summary className="cursor-pointer list-none font-medium text-neutral-900 dark:text-neutral-50">
                  Why this result?
                </summary>
                <div className="mt-3 space-y-1 text-neutral-500 dark:text-neutral-400">
                  <div>종합 점수 {hit.hybrid_score.toFixed(4)}</div>
                  {typeof hit.evidence_strength === 'number' ? <div>근거 강도 {hit.evidence_strength.toFixed(2)}</div> : null}
                  {typeof hit.vector_score === 'number' ? <div>의미 점수 {hit.vector_score.toFixed(4)}</div> : null}
                  {typeof hit.keyword_score === 'number' ? <div>키워드 점수 {hit.keyword_score.toFixed(4)}</div> : null}
                </div>
              </details>
            </Card>
          ))
        ) : (
          <Card className="p-10 text-center text-sm text-neutral-500">
            <Sparkles className="mx-auto mb-3 size-5 text-blue-500" />
            {mutation.data
              ? '조건에 맞는 결과가 없습니다.'
              : '질의를 입력하면 연결된 팀 지식에서 문서와 개념을 함께 찾아 드립니다.'}
            {authQuery.data?.authenticated ? (
              <div className="mt-4">
                <Button variant="outline" size="sm" onClick={() => window.location.assign('/new')}>
                  새 문서로 보완하기
                </Button>
              </div>
            ) : null}
          </Card>
        )}
      </div>
    </div>
  )
}
