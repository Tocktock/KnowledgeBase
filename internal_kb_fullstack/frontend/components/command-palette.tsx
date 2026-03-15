'use client'

import { useQuery } from '@tanstack/react-query'
import { FileText, Search, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'

import { Input } from '@/components/ui/input'
import type { DocumentListResponse } from '@/lib/types'
import { sentence } from '@/lib/utils'
import { useUiStore } from '@/store/ui-store'

async function fetchDocuments(query: string) {
  const search = new URLSearchParams({ limit: '8' })
  if (query.trim()) search.set('query', query.trim())
  const response = await fetch(`/api/documents?${search.toString()}`)
  if (!response.ok) throw new Error('문서 검색에 실패했습니다.')
  return (await response.json()) as DocumentListResponse
}

export function CommandPalette() {
  const { commandOpen, setCommandOpen } = useUiStore()
  const [query, setQuery] = useState('')

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen(!commandOpen)
      }
      if (event.key === 'Escape') setCommandOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [commandOpen, setCommandOpen])

  const enabled = commandOpen
  const { data, isLoading } = useQuery({
    queryKey: ['palette-documents', query],
    queryFn: () => fetchDocuments(query),
    enabled,
  })

  const items = useMemo(() => data?.items ?? [], [data])

  if (!commandOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-neutral-950/45 px-4 pt-24 backdrop-blur-sm">
      <div className="w-full max-w-2xl overflow-hidden rounded-3xl border border-neutral-200 bg-white shadow-2xl dark:border-neutral-800 dark:bg-neutral-950">
        <div className="border-b border-neutral-200 p-4 dark:border-neutral-800">
          <div className="flex items-center gap-3">
            <Search className="size-4 text-neutral-400" />
            <Input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="문서 제목, slug, 본문으로 바로 이동"
              className="border-none px-0 shadow-none focus:border-transparent"
            />
          </div>
        </div>

        <div className="max-h-[65vh] overflow-y-auto p-3">
          <div className="mb-3 flex items-center gap-2 px-2 text-xs font-medium uppercase tracking-[0.18em] text-neutral-400">
            <Sparkles className="size-3.5" /> quick open
          </div>
          {isLoading ? (
            <div className="rounded-2xl p-4 text-sm text-neutral-500">검색 중...</div>
          ) : items.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-neutral-200 p-6 text-sm text-neutral-500 dark:border-neutral-800">
              일치하는 문서가 없습니다.
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <Link
                  key={item.id}
                  href={`/docs/${item.slug}`}
                  onClick={() => setCommandOpen(false)}
                  className="block rounded-2xl border border-transparent px-4 py-3 transition hover:border-neutral-200 hover:bg-neutral-50 dark:hover:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                    <FileText className="size-4 text-blue-500" />
                    {item.title}
                  </div>
                  <div className="mb-2 text-xs text-neutral-400">/{item.slug}</div>
                  <p className="text-sm leading-6 text-neutral-600 dark:text-neutral-400">{sentence(item.excerpt)}</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
      <button className="absolute inset-0 -z-10" onClick={() => setCommandOpen(false)} aria-label="닫기" />
    </div>
  )
}
