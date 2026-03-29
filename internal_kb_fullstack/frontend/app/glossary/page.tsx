import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowRight } from 'lucide-react'

import { TrustBadges } from '@/components/trust/trust-badges'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getGlossaryConcepts } from '@/lib/api/server'
import { formatConceptTypeLabel, formatOwnerTeamLabel } from '@/lib/utils'

export default async function GlossaryPage() {
  const glossary = await getGlossaryConcepts({ status: 'approved', limit: 60 }).catch(() => null)
  if (glossary === null) notFound()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">핵심 개념</h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">
          반복해서 등장하는 팀 용어를 대표 문서와 근거 문서로 정리한 의미 레이어입니다.
        </p>
      </div>

      <Card className="p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex flex-wrap gap-2">
              <Badge>새 핵심 개념 요청</Badge>
            </div>
            <h2 className="text-xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">
              찾는 용어가 없다면 전용 요청 페이지에서 등록하세요.
            </h2>
            <p className="mt-2 text-sm leading-7 text-neutral-500">
              Concepts 목록은 승인된 개념 탐색에 집중하고, 신규 요청과 내 요청 상태 확인은 별도 페이지에서 처리합니다.
            </p>
          </div>
          <Link
            href="/glossary/requests"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-center text-sm font-medium text-white transition hover:bg-blue-500"
          >
            새 핵심 개념 요청 <ArrowRight className="size-4" />
          </Link>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {glossary.items.map((concept) => (
          <Link key={concept.id} href={`/glossary/${concept.slug}`}>
            <Card className="h-full p-5 transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 dark:hover:border-blue-900">
              <div className="mb-2 flex flex-wrap gap-2">
                <Badge>핵심 개념</Badge>
                <Badge>{formatConceptTypeLabel(concept.concept_type)}</Badge>
                {concept.owner_team_hint ? <Badge>{formatOwnerTeamLabel(concept.owner_team_hint)}</Badge> : null}
              </div>
              <div className="mb-1 line-clamp-2 text-lg font-semibold text-neutral-950 dark:text-neutral-50">{concept.display_term}</div>
              <div className="text-xs text-neutral-400">근거 문서 {concept.support_doc_count}개 · 신뢰도 {concept.confidence_score.toFixed(2)}</div>
              <div className="mt-3">
                <TrustBadges trust={concept.trust} />
              </div>
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
