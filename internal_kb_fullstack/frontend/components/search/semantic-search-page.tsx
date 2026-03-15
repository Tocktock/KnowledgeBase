'use client'

import { useMutation } from '@tanstack/react-query'
import { ArrowUpRight, Brain, Search, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { FormEvent, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { SearchRequest, SearchResponse } from '@/lib/types'

async function semanticSearch(payload: SearchRequest) {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error('검색에 실패했습니다.')
  return (await response.json()) as SearchResponse
}

export function SemanticSearchPage() {
  const [query, setQuery] = useState('배포 전 체크리스트')
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

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden p-6">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          <Brain className="size-4 text-blue-500" /> 하이브리드 검색
        </div>
        <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_200px_200px_auto]">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 롤백 기준과 배포 전 점검 항목" />
          <Input value={docType} onChange={(event) => setDocType(event.target.value)} placeholder="doc_type 선택" />
          <Input value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="owner_team 선택" />
          <Button type="submit" className="w-full">
            <Search className="size-4" /> 검색
          </Button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-neutral-500">
          <Badge>semantic + keyword</Badge>
          <Badge>pgvector + PostgreSQL FTS</Badge>
          <Badge>RRF fusion</Badge>
        </div>
      </Card>

      {mutation.isError ? (
        <Card className="p-5 text-sm text-red-600 dark:text-red-400">{mutation.error instanceof Error ? mutation.error.message : '오류가 발생했습니다.'}</Card>
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
        ) : mutation.data?.hits.length ? (
          mutation.data.hits.map((hit) => (
            <Card key={hit.chunk_id} className="p-5">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <Link href={`/docs/${hit.document_slug}`} className="text-lg font-semibold text-neutral-950 hover:text-blue-600 dark:text-neutral-50 dark:hover:text-blue-400">
                    {hit.document_title}
                  </Link>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-neutral-400">
                    <Badge>{hit.source_system}</Badge>
                    {hit.section_title ? <Badge>{hit.section_title}</Badge> : null}
                    {hit.heading_path.map((item) => (
                      <Badge key={item}>{item}</Badge>
                    ))}
                  </div>
                </div>
                <div className="text-right text-xs text-neutral-400">
                  <div>hybrid {hit.hybrid_score.toFixed(4)}</div>
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
            질의를 입력하면 벡터 검색과 키워드 검색을 합친 결과를 보여줍니다.
          </Card>
        )}
      </div>
    </div>
  )
}
