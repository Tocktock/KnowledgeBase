import Link from 'next/link'

import { Card } from '@/components/ui/card'
import type { DocumentRelationItem, DocumentRelationsResponse } from '@/lib/types'
import { sentence } from '@/lib/utils'

function Section({ title, items }: { title: string; items: DocumentRelationItem[] }) {
  return (
    <Card className="p-5">
      <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">{title}</div>
      {items.length === 0 ? (
        <p className="text-sm text-neutral-500">아직 연결된 문서가 없습니다.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Link key={item.id} href={`/docs/${item.slug}`} className="block rounded-2xl border border-transparent p-3 transition hover:border-neutral-200 hover:bg-neutral-50 dark:hover:border-neutral-800 dark:hover:bg-neutral-900">
              <div className="mb-1 text-sm font-medium text-neutral-900 dark:text-neutral-50">{item.title}</div>
              <div className="mb-2 text-xs text-neutral-400">/{item.slug}</div>
              <p className="text-sm leading-6 text-neutral-600 dark:text-neutral-400">{sentence(item.excerpt)}</p>
            </Link>
          ))}
        </div>
      )}
    </Card>
  )
}

export function DocumentRelations({ relations }: { relations: DocumentRelationsResponse }) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Section title="이 문서가 링크한 문서" items={relations.outgoing} />
      <Section title="이 문서를 가리키는 문서" items={relations.backlinks} />
      <Section title="관련 문서" items={relations.related} />
    </div>
  )
}
