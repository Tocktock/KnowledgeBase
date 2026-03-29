'use client'

import { useQuery } from '@tanstack/react-query'
import { Activity, CheckCircle2, Clock3, LoaderCircle, TriangleAlert } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { JobSummary } from '@/lib/types'
import { formatDate, formatJobKindLabel, formatJobTitle, formatStatusLabel } from '@/lib/utils'

const iconForStatus = {
  queued: Clock3,
  processing: LoaderCircle,
  completed: CheckCircle2,
  failed: TriangleAlert,
  cancelled: TriangleAlert,
} as const

async function fetchJobs() {
  const response = await fetch('/api/jobs', { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('동기화 작업 목록을 불러오지 못했습니다.')
  }
  return (await response.json()) as JobSummary[]
}

export function JobsPage() {
  const jobsQuery = useQuery({
    queryKey: ['jobs-page'],
    queryFn: fetchJobs,
  })
  const jobs = jobsQuery.data ?? []
  const queuedCount = jobs.filter((job) => job.status === 'queued').length
  const processingCount = jobs.filter((job) => job.status === 'processing').length
  const failedCount = jobs.filter((job) => job.status === 'failed').length

  return (
    <div className="space-y-4">
      {jobsQuery.isError ? (
        <Card className="p-5 text-sm text-red-600 dark:text-red-400">
          {jobsQuery.error instanceof Error ? jobsQuery.error.message : '동기화 작업 목록을 불러오지 못했습니다.'}
        </Card>
      ) : null}
      <Card className="p-5">
        <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">현재 동기화 상태</div>
        <div className="flex flex-wrap gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <Badge>대기 {queuedCount}</Badge>
          <Badge>처리 중 {processingCount}</Badge>
          <Badge>실패 {failedCount}</Badge>
          <Badge>최근 작업 {jobs.length}</Badge>
        </div>
      </Card>
      {jobsQuery.isLoading ? (
        Array.from({ length: 3 }).map((_, index) => (
          <Card key={index} className="animate-pulse p-5">
            <div className="mb-3 h-5 w-2/3 rounded bg-neutral-200 dark:bg-neutral-800" />
            <div className="mb-2 h-4 w-5/6 rounded bg-neutral-100 dark:bg-neutral-900" />
            <div className="h-4 w-2/3 rounded bg-neutral-100 dark:bg-neutral-900" />
          </Card>
        ))
      ) : jobs.length === 0 ? (
        <Card className="p-10 text-center text-sm text-neutral-500">
          <Activity className="mx-auto mb-3 size-5 text-blue-500" /> 아직 동기화 작업이 없습니다.
        </Card>
      ) : (
        jobs.map((job) => {
          const Icon = iconForStatus[job.status as keyof typeof iconForStatus] ?? Activity
          return (
            <Card key={job.id} className="p-5">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-base font-semibold text-neutral-950 dark:text-neutral-50">
                  <Icon className={`size-4 ${job.status === 'processing' ? 'animate-spin' : ''}`} />
                  {formatJobTitle(job.title)}
                </div>
                <Badge>{formatJobKindLabel(job.kind)}</Badge>
                <Badge>{formatStatusLabel(job.status)}</Badge>
                {job.embedding_model ? <Badge>{job.embedding_model}</Badge> : null}
                {typeof job.embedding_dimensions === 'number' ? <Badge>{job.embedding_dimensions}차원</Badge> : null}
                <Badge>우선순위 {job.priority}</Badge>
                <Badge>시도 {job.attempt_count}회</Badge>
              </div>
              <div className="grid gap-2 text-sm text-neutral-600 dark:text-neutral-400 md:grid-cols-3">
                <div>요청 시각: {formatDate(job.requested_at)}</div>
                <div>시작 시각: {formatDate(job.started_at)}</div>
                <div>완료 시각: {formatDate(job.finished_at)}</div>
              </div>
              {job.error_message ? (
                <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-950 dark:bg-red-950/30 dark:text-red-300">
                  {job.error_message}
                </div>
              ) : null}
            </Card>
          )
        })
      )}
    </div>
  )
}
