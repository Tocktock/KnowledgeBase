import Link from 'next/link'
import { notFound } from 'next/navigation'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getGlossaryConcepts } from '@/lib/api/server'
import { formatConceptTypeLabel, formatOwnerTeamLabel } from '@/lib/utils'

export const dynamic = 'force-dynamic'

export default async function GlossaryPage() {
  const glossary = await getGlossaryConcepts({ status: 'approved', limit: 60 }).catch(() => null)
  if (glossary === null) notFound()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">용어집</h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">
          승인된 개념 문서를 중심으로 탐색하는 개념 레이어입니다.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {glossary.items.map((concept) => (
          <Link key={concept.id} href={`/glossary/${concept.slug}`}>
            <Card className="h-full p-5 transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 dark:hover:border-blue-900">
              <div className="mb-2 flex flex-wrap gap-2">
                <Badge>용어집</Badge>
                <Badge>{formatConceptTypeLabel(concept.concept_type)}</Badge>
                {concept.owner_team_hint ? <Badge>{formatOwnerTeamLabel(concept.owner_team_hint)}</Badge> : null}
              </div>
              <div className="mb-1 text-lg font-semibold text-neutral-950 dark:text-neutral-50">{concept.display_term}</div>
              <div className="text-xs text-neutral-400">근거 문서 {concept.support_doc_count}개 · 신뢰도 {concept.confidence_score.toFixed(2)}</div>
              <p className="mt-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
                {concept.aliases.slice(0, 5).join(', ') || '대표 용어와 근거 문서로 정제된 개념입니다.'}
              </p>
              {concept.canonical_document ? (
                <div className="mt-4 text-sm text-blue-600 dark:text-blue-400">대표 문서 연결됨</div>
              ) : null}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
