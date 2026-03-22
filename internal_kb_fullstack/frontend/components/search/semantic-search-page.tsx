'use client'

import { useMutation } from '@tanstack/react-query'
import { ArrowUpRight, Brain, Search, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { FormEvent, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { SearchExplainResponse, SearchRequest, SearchResponse } from '@/lib/types'

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
  const [query, setQuery] = useState('센디 차량')
  const [docType, setDocType] = useState('')
  const [ownerTeam, setOwnerTeam] = useState('')

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
          <Brain className="size-4 text-blue-500" /> 컨셉 인지 검색
        </div>
        <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_200px_200px_auto]">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 센디 차량, 내부배차율, 화주 스쿼드" />
          <Input value={docType} onChange={(event) => setDocType(event.target.value)} placeholder="doc_type 선택" />
          <Input value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="owner_team 선택" />
          <Button type="submit" className="w-full">
            <Search className="size-4" /> 검색
          </Button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-neutral-500">
          <Badge>concept-aware reranking</Badge>
          <Badge>semantic + keyword</Badge>
          <Badge>evidence diversification</Badge>
          <Badge>용어집 우선 exact match</Badge>
        </div>
      </Card>

      {mutation.isError ? (
        <Card className="p-5 text-sm text-red-600 dark:text-red-400">{mutation.error instanceof Error ? mutation.error.message : '오류가 발생했습니다.'}</Card>
      ) : null}

      {explain ? (
        <Card className="p-5">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge>normalized {explain.normalized_query}</Badge>
            {explain.resolved_concept_term ? <Badge>concept {explain.resolved_concept_term}</Badge> : <Badge>concept unresolved</Badge>}
            {explain.resolved_concept_status ? <Badge>{explain.resolved_concept_status}</Badge> : null}
            {explain.canonical_document_slug ? <Badge>canonical /docs/{explain.canonical_document_slug}</Badge> : null}
            {explain.weak_grounding ? <Badge className="border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">weak grounding</Badge> : null}
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
            <div className="text-sm text-neutral-500">현재 질의에 대해 개념 해석과 근거 번들을 함께 표시합니다.</div>
          )}
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
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-neutral-400">
                    <Badge>{hit.result_type ?? 'document'}</Badge>
                    <Badge>{hit.source_system}</Badge>
                    {hit.matched_concept_term ? <Badge>concept {hit.matched_concept_term}</Badge> : null}
                    {hit.evidence_kind ? <Badge>{hit.evidence_kind}</Badge> : null}
                    {hit.section_title ? <Badge>{hit.section_title}</Badge> : null}
                    {hit.heading_path.map((item) => (
                      <Badge key={item}>{item}</Badge>
                    ))}
                  </div>
                </div>
                <div className="text-right text-xs text-neutral-400">
                  <div>hybrid {hit.hybrid_score.toFixed(4)}</div>
                  {typeof hit.evidence_strength === 'number' ? <div>evidence {hit.evidence_strength.toFixed(2)}</div> : null}
                  {typeof hit.vector_score === 'number' ? <div>vector {hit.vector_score.toFixed(4)}</div> : null}
                  {typeof hit.keyword_score === 'number' ? <div>keyword {hit.keyword_score.toFixed(4)}</div> : null}
                </div>
              </div>
              <p className="text-sm leading-7 text-neutral-600 dark:text-neutral-400">{hit.content_text}</p>
              <div className="mt-4 flex justify-end">
                <Link href={`/docs/${hit.document_slug}`} className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                  문서 열기
                  <ArrowUpRight className="size-4" />
                </Link>
              </div>
            </Card>
          ))
        ) : (
          <Card className="p-10 text-center text-sm text-neutral-500">
            <Sparkles className="mx-auto mb-3 size-5 text-blue-500" />
            질의를 입력하면 컨셉 해석, 근거 설명, 검색 결과를 함께 보여줍니다.
          </Card>
        )}
      </div>
    </div>
  )
}
