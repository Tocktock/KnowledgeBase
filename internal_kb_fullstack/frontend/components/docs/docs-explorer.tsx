'use client'

import { useQuery } from '@tanstack/react-query'
import { BookCopy, Filter, Search } from 'lucide-react'
import Link from 'next/link'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { DocumentListResponse } from '@/lib/types'
import { formatDate, formatDocTypeLabel, sentence } from '@/lib/utils'

async function fetchDocuments(params: Record<string, string>) {
  const search = new URLSearchParams(params)
  const response = await fetch(`/api/documents?${search.toString()}`)
  if (!response.ok) throw new Error('문서 목록을 불러오지 못했습니다.')
  return (await response.json()) as DocumentListResponse
}

export function DocsExplorer() {
  const [query, setQuery] = useState('')
  const [ownerTeam, setOwnerTeam] = useState('')
  const [docType, setDocType] = useState('')

  const params = useMemo(() => {
    const next: Record<string, string> = { limit: '40' }
    if (query.trim()) next.query = query.trim()
    if (ownerTeam.trim()) next.owner_team = ownerTeam.trim()
    if (docType.trim()) next.doc_type = docType.trim()
    return next
  }, [docType, ownerTeam, query])

  const { data, isLoading, error } = useQuery({
    queryKey: ['documents', params],
    queryFn: () => fetchDocuments(params),
  })

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          <Filter className="size-4 text-blue-500" /> 탐색 필터
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="제목 / slug / 본문 검색" />
          <Input value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="팀 필터" />
          <Input value={docType} onChange={(event) => setDocType(event.target.value)} placeholder="문서 타입 필터" />
        </div>
      </Card>

      {error ? (
        <Card className="p-5 text-sm text-red-600 dark:text-red-400">{error instanceof Error ? error.message : '오류가 발생했습니다.'}</Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, index) => (
              <Card key={index} className="animate-pulse p-5">
                <div className="mb-4 h-5 w-2/3 rounded bg-neutral-200 dark:bg-neutral-800" />
                <div className="mb-2 h-3 w-1/2 rounded bg-neutral-200 dark:bg-neutral-800" />
                <div className="h-16 rounded bg-neutral-100 dark:bg-neutral-900" />
              </Card>
            ))
          : data?.items.map((item) => (
              <Link key={item.id} href={`/docs/${item.slug}`}>
                <Card className="group h-full p-5 transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 dark:hover:border-blue-900">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <div className="mb-1 flex items-center gap-2 text-lg font-semibold text-neutral-950 dark:text-neutral-50">
                        <BookCopy className="size-4 text-blue-500" />
                        <span className="line-clamp-1">{item.title}</span>
                      </div>
                      <div className="text-xs text-neutral-400">/{item.slug}</div>
                    </div>
                    <Badge>{formatDocTypeLabel(item.doc_type)}</Badge>
                  </div>
                  <p className="mb-4 line-clamp-4 text-sm leading-7 text-neutral-600 dark:text-neutral-400">{sentence(item.excerpt, 220)}</p>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-400">
                    {item.owner_team ? <Badge>{item.owner_team}</Badge> : null}
                    <Badge>{item.status}</Badge>
                    <span>{formatDate(item.updated_at)}</span>
                  </div>
                </Card>
              </Link>
            ))}
      </div>

      {!isLoading && data?.items.length === 0 ? (
        <Card className="p-10 text-center">
          <Search className="mx-auto mb-3 size-5 text-neutral-400" />
          <div className="text-sm text-neutral-500">조건에 맞는 문서가 없습니다.</div>
        </Card>
      ) : null}
    </div>
  )
}
