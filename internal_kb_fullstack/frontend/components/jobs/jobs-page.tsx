import { Activity, CheckCircle2, Clock3, LoaderCircle, TriangleAlert } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { JobSummary } from '@/lib/types'
import { formatDate } from '@/lib/utils'

const iconForStatus = {
  queued: Clock3,
  processing: LoaderCircle,
  completed: CheckCircle2,
  failed: TriangleAlert,
  cancelled: TriangleAlert,
} as const

export function JobsPage({ jobs }: { jobs: JobSummary[] }) {
  return (
    <div className="space-y-4">
      {jobs.length === 0 ? (
        <Card className="p-10 text-center text-sm text-neutral-500">
          <Activity className="mx-auto mb-3 size-5 text-blue-500" /> 아직 작업이 없습니다.
        </Card>
      ) : (
        jobs.map((job) => {
          const Icon = iconForStatus[job.status as keyof typeof iconForStatus] ?? Activity
          return (
            <Card key={job.id} className="p-5">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-base font-semibold text-neutral-950 dark:text-neutral-50">
                  <Icon className={`size-4 ${job.status === 'processing' ? 'animate-spin' : ''}`} />
                  {job.title}
                </div>
                <Badge>{job.kind}</Badge>
                <Badge>{job.status}</Badge>
                {job.embedding_model ? <Badge>{job.embedding_model}</Badge> : null}
                {typeof job.embedding_dimensions === 'number' ? <Badge>{job.embedding_dimensions} dims</Badge> : null}
                <Badge>priority {job.priority}</Badge>
                <Badge>attempt {job.attempt_count}</Badge>
              </div>
              <div className="grid gap-2 text-sm text-neutral-600 dark:text-neutral-400 md:grid-cols-3">
                <div>requested: {formatDate(job.requested_at)}</div>
                <div>started: {formatDate(job.started_at)}</div>
                <div>finished: {formatDate(job.finished_at)}</div>
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
