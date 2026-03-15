import { BookMarked, Clock3, FileText, Link2 } from 'lucide-react'
import { notFound } from 'next/navigation'
import Link from 'next/link'

import { DocumentRelations } from '@/components/docs/document-relations'
import { MarkdownRenderer } from '@/components/docs/markdown-renderer'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getDocumentBySlug, getDocumentRelations } from '@/lib/api/server'
import type { DocumentRelationsResponse } from '@/lib/types'
import { formatDate } from '@/lib/utils'

export const dynamic = 'force-dynamic'

export default async function DocumentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params

  const data = await getDocumentBySlug(slug).catch(() => notFound())
  const relations: DocumentRelationsResponse = await getDocumentRelations(data.document.id, 8).catch(() => ({ outgoing: [], backlinks: [], related: [] }))
  const markdown = data.content_markdown ?? data.content_text ?? ''
  const headings = data.headings
  const linkedSlugs = data.linked_slugs

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-6">
        <Card className="overflow-hidden p-7 md:p-8">
          <div className="mb-4 flex flex-wrap gap-2">
            <Badge>{data.document.doc_type}</Badge>
            <Badge>{data.document.status}</Badge>
            {data.document.owner_team ? <Badge>{data.document.owner_team}</Badge> : null}
            <Badge>{data.document.language_code}</Badge>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">{data.document.title}</h1>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-neutral-500 dark:text-neutral-400">
            <div className="inline-flex items-center gap-2"><FileText className="size-4" /> /{data.document.slug}</div>
            <div className="inline-flex items-center gap-2"><Clock3 className="size-4" /> 업데이트 {formatDate(data.document.updated_at)}</div>
            {data.revision ? <div className="inline-flex items-center gap-2"><BookMarked className="size-4" /> rev {data.revision.revision_number}</div> : null}
            <div className="inline-flex items-center gap-2"><Link2 className="size-4" /> 링크 {linkedSlugs.length}개</div>
          </div>
          {data.document.source_url ? (
            <div className="mt-4 text-sm text-neutral-500">
              source:{' '}
              <a className="text-blue-600 underline decoration-blue-200 underline-offset-4 dark:text-blue-400" href={data.document.source_url} target="_blank" rel="noreferrer">
                {data.document.source_url}
              </a>
            </div>
          ) : null}
        </Card>

        <Card className="p-7 md:p-8">
          <MarkdownRenderer markdown={markdown} />
        </Card>

        <DocumentRelations relations={relations} />
      </div>

      <div className="space-y-4">
        <Card className="sticky top-24 p-5">
          <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">문서 개요</div>
          <div className="space-y-2">
            {headings.length === 0 ? (
              <div className="text-sm text-neutral-500">목차가 없습니다.</div>
            ) : (
              headings.map((heading) => (
                <a key={heading.id} href={`#${heading.id}`} className="block rounded-xl px-3 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50 hover:text-neutral-950 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-neutral-50">
                  {heading.title}
                </a>
              ))
            )}
          </div>
          {linkedSlugs.length > 0 ? (
            <>
              <div className="mb-3 mt-6 text-sm font-semibold text-neutral-900 dark:text-neutral-50">문서 내 링크</div>
              <div className="flex flex-wrap gap-2">
                {linkedSlugs.map((item) => (
                  <Link key={item} href={`/docs/${item}`} className="rounded-full border border-neutral-200 px-3 py-1 text-xs text-neutral-600 transition hover:border-blue-300 hover:text-blue-600 dark:border-neutral-800 dark:text-neutral-400 dark:hover:border-blue-900 dark:hover:text-blue-400">
                    {item}
                  </Link>
                ))}
              </div>
            </>
          ) : null}
        </Card>
      </div>
    </div>
  )
}
