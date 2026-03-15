import { ArrowRight, BookOpenText, Brain, Clock3, Sparkles, Workflow } from 'lucide-react'
import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { getJobs, getRecentDocuments } from '@/lib/api/server'
import type { DocumentListItem, JobSummary } from '@/lib/types'
import { formatDate, sentence } from '@/lib/utils'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  const [documentsResult, jobsResult] = await Promise.allSettled([getRecentDocuments(9), getJobs()])
  const documents: DocumentListItem[] = documentsResult.status === 'fulfilled' ? documentsResult.value.items : []
  const jobs: JobSummary[] = jobsResult.status === 'fulfilled' ? jobsResult.value.slice(0, 5) : []

  return (
    <div className="space-y-8">
      <Card className="overflow-hidden p-8 md:p-10">
        <div className="max-w-3xl">
          <div className="mb-4 flex flex-wrap gap-2">
            <Badge>Next.js 16</Badge>
            <Badge>React 19</Badge>
            <Badge>Tiptap 3</Badge>
            <Badge>Tailwind 4</Badge>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50 md:text-5xl">
            노션처럼 쓰고,
            <br className="hidden md:block" />
            위키처럼 연결되는 사내 지식 베이스.
          </h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-8 text-neutral-600 dark:text-neutral-400">
            문서 작성은 깔끔하고 집중감 있게, 문서 탐색은 링크 중심으로 빠르게. 현재 백엔드는 PostgreSQL, pgvector, 하이브리드 검색 파이프라인에 맞춰 연결돼 있습니다.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/new"><Button><Sparkles className="size-4" /> 새 문서 작성</Button></Link>
            <Link href="/search"><Button variant="outline"><Brain className="size-4" /> 시맨틱 검색</Button></Link>
            <Link href="/docs"><Button variant="outline"><BookOpenText className="size-4" /> 문서 탐색</Button></Link>
          </div>
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
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Workflow className="size-4 text-blue-500" /> 임베딩 작업</div>
          <div className="space-y-3">
            {jobs.length === 0 ? (
              <div className="rounded-2xl bg-neutral-50 p-4 text-sm text-neutral-500 dark:bg-neutral-900">작업 이력이 아직 없습니다.</div>
            ) : (
              jobs.map((job) => (
                <div key={job.id} className="rounded-2xl border border-neutral-200 p-4 dark:border-neutral-800">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <Badge>{job.status}</Badge>
                    <span className="text-xs text-neutral-400">{job.embedding_model}</span>
                  </div>
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
            <div className="rounded-2xl bg-neutral-50 p-4 dark:bg-neutral-900">2. 백엔드가 청크와 임베딩을 만들고 검색 인덱스를 갱신합니다.</div>
            <div className="rounded-2xl bg-neutral-50 p-4 dark:bg-neutral-900">3. 시맨틱 검색과 위키형 링크 탐색으로 문서를 연결해서 찾습니다.</div>
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">문서 컬렉션 미리보기</div>
            <div className="mt-1 text-sm text-neutral-500">최근 업데이트된 문서를 둘러보세요.</div>
          </div>
          <Link href="/docs" className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
            전체 보기 <ArrowRight className="size-4" />
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {documents.map((document) => (
            <Link key={document.id} href={`/docs/${document.slug}`}>
              <Card className="h-full p-5 transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 dark:hover:border-blue-900">
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge>{document.doc_type}</Badge>
                  {document.owner_team ? <Badge>{document.owner_team}</Badge> : null}
                </div>
                <div className="mb-1 text-lg font-semibold text-neutral-950 dark:text-neutral-50">{document.title}</div>
                <div className="text-xs text-neutral-400">/{document.slug}</div>
                <p className="mt-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">{sentence(document.excerpt, 200)}</p>
              </Card>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  )
}
