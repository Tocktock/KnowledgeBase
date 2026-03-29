'use client'

import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  BookMarked,
  BookOpenText,
  CheckCircle2,
  Link2,
  LoaderCircle,
  Search,
  ShieldCheck,
  TriangleAlert,
  Workflow,
} from 'lucide-react'
import Link from 'next/link'

import { TrustBadges } from '@/components/trust/trust-badges'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { WorkspaceOverviewResponse } from '@/lib/types'
import {
  formatConceptTypeLabel,
  formatDate,
  formatDocTypeLabel,
  sentence,
} from '@/lib/utils'

async function fetchOverview() {
  const response = await fetch('/api/workspace/overview', { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('워크스페이스 개요를 불러오지 못했습니다.')
  }
  return (await response.json()) as WorkspaceOverviewResponse
}

function setupStateLabel(value: string) {
  if (value === 'ready') return '운영 가능'
  if (value === 'attention_required') return '조치 필요'
  if (value === 'setup_needed') return '초기 설정 필요'
  return '확인 중'
}

export function WorkspaceHomePage() {
  const overviewQuery = useQuery({
    queryKey: ['workspace-overview'],
    queryFn: fetchOverview,
  })

  if (overviewQuery.isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 text-sm text-neutral-500">
          <LoaderCircle className="size-4 animate-spin" /> 워크스페이스 지식 레이어를 불러오는 중입니다.
        </div>
      </Card>
    )
  }

  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <Card className="p-6 text-sm text-red-600 dark:text-red-400">
        {overviewQuery.error instanceof Error ? overviewQuery.error.message : '홈 화면을 불러오지 못했습니다.'}
      </Card>
    )
  }

  const overview = overviewQuery.data
  const isAnonymous = !overview.authenticated
  const needsWorkspaceAccess = overview.authenticated && !overview.workspace
  const isAdmin = !needsWorkspaceAccess && overview.can_manage_connectors

  const heroTitle = isAnonymous
    ? '흩어진 팀 문서를 신뢰 가능한 워크스페이스 지식으로 바꿉니다.'
    : needsWorkspaceAccess
      ? '로그인은 완료됐지만 워크스페이스 초대가 필요합니다.'
      : '흩어진 팀 문서를 신뢰 가능한 워크스페이스 지식으로 바꿉니다.'
  const heroDescription = isAnonymous
    ? '관리자는 Google Drive, GitHub, Notion을 한 번 연결하고, 구성원은 검색과 문서 탐색만으로 최신 지식을 바로 찾습니다. 연결 구조나 동기화 내부를 이해할 필요는 없습니다.'
    : needsWorkspaceAccess
      ? '이 계정은 아직 워크스페이스 멤버십이 없습니다. 관리자에게 초대 링크를 요청하고 수락을 완료하면 검색, 문서, 핵심 개념 화면이 워크스페이스 기준으로 전환됩니다.'
      : '관리자는 Google Drive, GitHub, Notion을 한 번 연결하고, 구성원은 검색과 문서 탐색만으로 최신 지식을 바로 찾습니다. 연결 구조나 동기화 내부를 이해할 필요는 없습니다.'

  return (
    <div className="space-y-8">
      <Card className="overflow-hidden p-6 md:p-8">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(300px,360px)]">
          <div>
            <div className="mb-3 flex flex-wrap gap-2">
              <Badge>Workspace Knowledge Layer</Badge>
              {!isAnonymous && overview.workspace ? <Badge>{overview.workspace.name}</Badge> : null}
              {!isAnonymous && overview.viewer_role ? <Badge>{overview.viewer_role}</Badge> : null}
              {needsWorkspaceAccess ? <Badge>워크스페이스 초대 필요</Badge> : null}
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 md:text-4xl dark:text-neutral-50">
              {heroTitle}
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-neutral-600 dark:text-neutral-400">
              {heroDescription}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {isAnonymous ? (
                <>
                  <Button onClick={() => window.location.assign('/login?return_to=%2F')}>
                    로그인하고 시작하기
                  </Button>
                  <Button variant="outline" onClick={() => window.location.assign('/connectors')}>
                    데이터 소스 보기
                  </Button>
                </>
              ) : needsWorkspaceAccess ? (
                <Button variant="outline" onClick={() => window.location.assign('/connectors')}>
                  데이터 소스 보기
                </Button>
              ) : (
                <>
                  <Button onClick={() => window.location.assign('/search')}>
                    워크스페이스 검색 <Search className="size-4" />
                  </Button>
                  <Button variant="outline" onClick={() => window.location.assign('/docs')}>
                    문서 탐색
                  </Button>
                  {isAdmin ? (
                    <Button variant="outline" onClick={() => window.location.assign('/connectors')}>
                      데이터 소스 관리
                    </Button>
                  ) : null}
                </>
              )}
            </div>
          </div>

          <div className="space-y-3 rounded-3xl border border-neutral-200 bg-white/70 p-5 dark:border-neutral-800 dark:bg-neutral-950/60">
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              {isAnonymous
                ? '이 제품이 하는 일'
                : needsWorkspaceAccess
                  ? '다음 단계'
                  : isAdmin
                    ? '워크스페이스 상태'
                    : '바로 할 수 있는 일'}
            </div>
            <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
              {isAnonymous ? (
                <>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">1. 관리자가 팀 데이터 소스를 연결합니다.</div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">2. 문서가 자동으로 동기화되어 검색과 개념 레이어에 반영됩니다.</div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">3. 구성원은 검색과 문서 탐색만으로 답을 찾습니다.</div>
                </>
              ) : needsWorkspaceAccess ? (
                <>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">1. 워크스페이스 관리자에게 초대 링크를 요청합니다.</div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">2. 받은 초대 링크를 열어 멤버십을 수락합니다.</div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">3. 수락이 끝나면 홈, 검색, 문서, 핵심 개념 화면이 워크스페이스 기준으로 전환됩니다.</div>
                </>
              ) : isAdmin ? (
                <>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                    연결된 워크스페이스 소스 {overview.source_health.workspace_connection_count}개
                  </div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                    정상 소스 {overview.source_health.healthy_source_count}개 · 주의 필요 {overview.source_health.needs_attention_count}개
                  </div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                    현재 상태: {overview.setup_state === 'ready' ? '운영 가능' : overview.setup_state === 'attention_required' ? '조치 필요' : '초기 설정 필요'}
                  </div>
                </>
              ) : (
                <>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">검색에서 바로 문서를 찾고, 출처와 최신성을 함께 확인할 수 있습니다.</div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">핵심 개념에서 반복되는 용어와 대표 문서를 빠르게 이해할 수 있습니다.</div>
                  <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">데이터 소스 관리는 워크스페이스 관리자가 담당합니다.</div>
                </>
              )}
            </div>
          </div>
        </div>
      </Card>

      {isAdmin ? (
        <Card className="p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">다음으로 해야 할 일</div>
              <div className="mt-1 text-sm text-neutral-500">관리자 한 번의 설정으로 구성원 전체가 같은 지식 레이어를 사용합니다.</div>
            </div>
            <Badge>{setupStateLabel(overview.setup_state)}</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {overview.next_actions.map((item) => (
              <div key={item} className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm leading-7 text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
                {item}
              </div>
            ))}
            <Link href="/connectors" className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-4 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-300 dark:hover:bg-blue-950/40">
              데이터 소스 설정 열기 <ArrowRight className="ml-1 inline size-4" />
            </Link>
          </div>
          {overview.recent_sync_issues.length > 0 ? (
            <div className="mt-5 space-y-3">
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">최근 동기화 이슈</div>
              {overview.recent_sync_issues.map((job) => (
                <div key={job.id} className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/20 dark:text-amber-300">
                  <div className="flex items-center gap-2 font-medium">
                    <TriangleAlert className="size-4" /> {job.title}
                  </div>
                  <div className="mt-1 text-xs">요청 {formatDate(job.requested_at)}</div>
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-neutral-200 px-4 py-4 dark:border-neutral-800">
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">지식 검수 현황</div>
              <div className="mt-2 text-sm text-neutral-500">
                지금 검토가 필요한 용어 {overview.review_required_count}개
              </div>
              <div className="mt-2 text-xs text-neutral-400">
                최근 실행{' '}
                {overview.latest_validation_run
                  ? `${formatDate(overview.latest_validation_run.requested_at)} · ${String(
                      overview.latest_validation_run.validation_summary.updated_concepts ?? 0,
                    )}개 반영`
                  : '아직 없음'}
              </div>
            </div>
            <Link
              href="/glossary/review"
              className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-4 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-300 dark:hover:bg-blue-950/40"
            >
              지식 검수 열기 <ArrowRight className="ml-1 inline size-4" />
              <div className="mt-2 text-xs font-normal text-blue-700/80 dark:text-blue-300/80">
                동기화 후 변경분 검증과 용어 정의 검토를 한 곳에서 처리합니다.
              </div>
            </Link>
          </div>
        </Card>
      ) : null}

      {needsWorkspaceAccess ? (
        <Card className="p-6">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            <CheckCircle2 className="size-4 text-blue-500" /> 로그인 상태
          </div>
          <div className="text-sm leading-7 text-neutral-600 dark:text-neutral-400">
            로그인은 완료됐지만 아직 이 계정에 연결된 워크스페이스가 없습니다. 초대 수락이 끝나면 검색, 문서, 핵심 개념, 지식 검수 화면이 현재 워크스페이스 기준으로 활성화됩니다.
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {overview.next_actions.map((item) => (
              <div key={item} className="rounded-2xl border border-neutral-200 px-4 py-4 text-sm leading-7 text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
                {item}
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.2fr)_420px]">
          <Card className="p-6">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <BookOpenText className="size-4 text-blue-500" /> 추천 문서
            </div>
            <div className="space-y-3">
              {overview.featured_docs.map((document) => (
                <Link key={document.id} href={`/docs/${document.slug}`} className="block rounded-2xl border border-neutral-200 px-4 py-4 transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 dark:border-neutral-800 dark:hover:border-blue-900">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <div className="min-w-0 break-words font-medium text-neutral-900 dark:text-neutral-50">{document.title}</div>
                    <Badge>{formatDocTypeLabel(document.doc_type)}</Badge>
                  </div>
                  <TrustBadges trust={document.trust} />
                  <p className="mt-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">{sentence(document.excerpt, 200)}</p>
                  <div className="mt-3 text-xs text-neutral-400">
                    마지막 갱신 {formatDate(document.trust.last_synced_at ?? document.updated_at)}
                  </div>
                </Link>
              ))}
            </div>
          </Card>

          <div className="space-y-6">
            <Card className="p-6">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                <BookMarked className="size-4 text-blue-500" /> 핵심 개념
              </div>
              <div className="space-y-3">
                {overview.featured_concepts.map((concept) => (
                  <Link key={concept.id} href={`/glossary/${concept.slug}`} className="block rounded-2xl border border-neutral-200 px-4 py-4 transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/5 dark:border-neutral-800 dark:hover:border-blue-900">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <div className="min-w-0 break-words font-medium text-neutral-900 dark:text-neutral-50">{concept.display_term}</div>
                      <Badge>{formatConceptTypeLabel(concept.concept_type)}</Badge>
                    </div>
                    <TrustBadges trust={concept.trust} />
                    <div className="mt-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
                      근거 문서 {concept.support_doc_count}개 · 별칭 {concept.aliases.slice(0, 4).join(', ') || '없음'}
                    </div>
                  </Link>
                ))}
              </div>
            </Card>

            <Card className="p-6">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                <Workflow className="size-4 text-blue-500" /> 연결된 데이터가 만드는 효과
              </div>
              <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
                <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                  검색 결과는 출처와 최신성 정보를 함께 보여 줍니다.
                </div>
                <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                  핵심 개념은 반복되는 팀 용어를 정리해 문서를 더 쉽게 재사용하게 합니다.
                </div>
                <div className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">
                  관리자는 연결 상태만 관리하고, 구성원은 문서 탐색과 검색에 집중합니다.
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
