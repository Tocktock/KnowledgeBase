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

export function JobsPage({ jobs }: { jobs: JobSummary[] }) {
  const queuedCount = jobs.filter((job) => job.status === 'queued').length
  const processingCount = jobs.filter((job) => job.status === 'processing').length
  const failedCount = jobs.filter((job) => job.status === 'failed').length

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">현재 동기화 상태</div>
        <div className="flex flex-wrap gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <Badge>대기 {queuedCount}</Badge>
          <Badge>처리 중 {processingCount}</Badge>
          <Badge>실패 {failedCount}</Badge>
          <Badge>최근 작업 {jobs.length}</Badge>
        </div>
      </Card>
      {jobs.length === 0 ? (
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
