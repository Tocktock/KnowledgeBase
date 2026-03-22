import Link from 'next/link'
import { notFound } from 'next/navigation'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getGlossaryConceptBySlug } from '@/lib/api/server'
import { formatDocTypeLabel } from '@/lib/utils'

export const dynamic = 'force-dynamic'

export default async function GlossaryDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const detail = await getGlossaryConceptBySlug(slug).catch(() => null)
  if (detail === null) notFound()

  return (
    <div className="space-y-6">
      <Card className="p-7 md:p-8">
        <div className="mb-4 flex flex-wrap gap-2">
          <Badge>용어집</Badge>
          <Badge>{detail.concept.status}</Badge>
          <Badge>{detail.concept.concept_type}</Badge>
          {detail.concept.owner_team_hint ? <Badge>{detail.concept.owner_team_hint}</Badge> : null}
        </div>
        <h1 className="text-4xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">{detail.concept.display_term}</h1>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-neutral-500 dark:text-neutral-400">
          <div>normalized {detail.concept.normalized_term}</div>
          <div>{detail.concept.support_doc_count} docs</div>
          <div>score {detail.concept.confidence_score.toFixed(2)}</div>
        </div>
        <div className="mt-4 rounded-2xl bg-neutral-50 px-4 py-3 text-sm leading-7 text-neutral-600 dark:bg-neutral-900 dark:text-neutral-400">
          별칭: {detail.concept.aliases.length ? detail.concept.aliases.join(', ') : '없음'}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {detail.concept.canonical_document ? (
            <Link href={`/docs/${detail.concept.canonical_document.slug}`} className="text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
              canonical 문서 열기
            </Link>
          ) : null}
          {detail.concept.generated_document ? (
            <Link href={`/docs/${detail.concept.generated_document.slug}`} className="text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
              draft 문서 열기
            </Link>
          ) : null}
        </div>
      </Card>

      <Card className="p-6">
        <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">근거 문서</div>
        <div className="space-y-3">
          {detail.supports.slice(0, 20).map((support) => (
            <div key={support.id} className="rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
              <div className="mb-2 flex flex-wrap gap-2">
                <Badge>{support.evidence_kind}</Badge>
                <Badge>{support.evidence_strength.toFixed(2)}</Badge>
                <Badge>{formatDocTypeLabel(support.document_doc_type)}</Badge>
              </div>
              <Link href={`/docs/${support.document_slug}`} className="font-medium text-neutral-900 hover:text-blue-600 dark:text-neutral-50 dark:hover:text-blue-400">
                {support.document_title}
              </Link>
              <div className="mt-2 text-sm leading-7 text-neutral-600 dark:text-neutral-400">{support.support_text}</div>
            </div>
          ))}
        </div>
      </Card>

      {detail.related_concepts.length ? (
        <Card className="p-6">
          <div className="mb-4 text-sm font-semibold text-neutral-900 dark:text-neutral-50">관련 개념</div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
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
  )
}
