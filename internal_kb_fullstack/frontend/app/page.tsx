import { ArrowRight, BookMarked, BookOpenText, Clock3, Database, Workflow } from 'lucide-react'
import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getGlossaryConcepts, getJobs, getRecentDocuments } from '@/lib/api/server'
import { documentDomains } from '@/lib/document-domains'
import type { DocumentListItem, GlossaryConceptSummary, JobSummary } from '@/lib/types'
import {
  formatConceptTypeLabel,
  formatDate,
  formatJobKindLabel,
  formatJobTitle,
  formatOwnerTeamLabel,
  formatStatusLabel,
  sentence,
} from '@/lib/utils'

export const dynamic = 'force-dynamic'

const domainIcons = {
  knowledge: BookOpenText,
  'operations-design': Workflow,
  data: Database,
  glossary: BookMarked,
} as const

export default async function HomePage() {
  const [documentsResult, jobsResult, glossaryResult] = await Promise.allSettled([
    getRecentDocuments(5),
    getJobs(),
    getGlossaryConcepts({ status: 'approved', limit: 6 }),
  ])
  const documents: DocumentListItem[] = documentsResult.status === 'fulfilled' ? documentsResult.value.items : []
  const jobs: JobSummary[] = jobsResult.status === 'fulfilled' ? jobsResult.value.slice(0, 5) : []
  const glossary: GlossaryConceptSummary[] = glossaryResult.status === 'fulfilled' ? glossaryResult.value.items : []

  return (
    <div className="space-y-8">
      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">문서 구성 한눈에 보기</div>
            <div className="mt-1 text-sm text-neutral-500">이 지식 베이스가 다루는 문서 층을 빠르게 이해할 수 있습니다.</div>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {documentDomains.map((domain) => {
            const Icon = domainIcons[domain.key]
            return (
              <Link key={domain.key} href={domain.href} className="block h-full">
                <Card
                  className="flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 focus-within:border-blue-300 focus-within:shadow-lg focus-within:shadow-blue-500/5 dark:hover:border-blue-900"
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <Badge>{domain.badge}</Badge>
                    <Icon className="size-5 text-blue-500" />
                  </div>
                  <div className="mb-2 text-lg font-semibold text-neutral-950 dark:text-neutral-50">{domain.title}</div>
                  <p className="mb-5 text-sm leading-7 text-neutral-600 dark:text-neutral-400">{domain.description}</p>
                  <div className="mt-auto inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                    {domain.cta} <ArrowRight className="size-4" />
                  </div>
                </Card>
              </Link>
            )
          })}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-6">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><BookOpenText className="size-4 text-blue-500" /> 최근 문서</div>
          <div className="space-y-3">
            {documents.slice(0, 5).map((document) => (
              <Link key={document.id} href={`/docs/${document.slug}`} className="block rounded-2xl p-3 transition hover:bg-neutral-50 dark:hover:bg-neutral-900">
                <div className="font-medium text-neutral-900 dark:text-neutral-50">{document.title}</div>
                <div className="mt-1 text-xs text-neutral-400">/{document.slug}</div>
                <p className="mt-2 text-sm leading-6 text-neutral-600 dark:text-neutral-400">{sentence(document.excerpt)}</p>
              </Link>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Workflow className="size-4 text-blue-500" /> 최근 처리 작업</div>
          <div className="space-y-3">
            {jobs.length === 0 ? (
              <div className="rounded-2xl bg-neutral-50 p-4 text-sm text-neutral-500 dark:bg-neutral-900">작업 이력이 아직 없습니다.</div>
            ) : (
              jobs.map((job) => (
                <div key={job.id} className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <Badge>{formatStatusLabel(job.status)}</Badge>
                    <span className="text-xs text-neutral-400">{formatJobKindLabel(job.kind)}</span>
                  </div>
                  <div className="mb-1 text-sm font-medium text-neutral-800 dark:text-neutral-100">{formatJobTitle(job.title)}</div>
                  <div className="text-sm text-neutral-600 dark:text-neutral-400">{formatDate(job.requested_at)}</div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Clock3 className="size-4 text-blue-500" /> 추천 워크플로</div>
          <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
            <div className="rounded-2xl bg-neutral-50 p-4 dark:bg-neutral-900">1. 새 문서를 작성하거나 기존 markdown/html 파일을 업로드합니다.</div>
            <div className="rounded-2xl bg-neutral-50 p-4 dark:bg-neutral-900">2. 시스템이 본문을 검색 가능한 단위로 정리하고 검색 인덱스를 갱신합니다.</div>
            <div className="rounded-2xl bg-neutral-50 p-4 dark:bg-neutral-900">3. 용어집 리뷰 스튜디오에서 개념을 다듬고, 시맨틱 검색과 위키형 링크 탐색으로 연결된 지식을 찾습니다.</div>
          </div>
        </Card>
      </div>

      {glossary.length ? (
        <Card className="p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">승인된 용어집</div>
              <div className="mt-1 text-sm text-neutral-500">정제된 개념 문서를 바로 탐색하세요.</div>
            </div>
            <Link href="/glossary" className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
              전체 보기 <ArrowRight className="size-4" />
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {glossary.map((concept) => (
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
                    {concept.aliases.slice(0, 4).join(', ') || '대표 용어로 정제된 개념입니다.'}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  )
}
