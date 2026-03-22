import { JobsPage } from '@/components/jobs/jobs-page'
import { getJobs } from '@/lib/api/server'

export const dynamic = 'force-dynamic'

export default async function JobsRoutePage() {
  const jobs = await getJobs().catch(() => [])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">인덱싱 작업</h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">문서 처리와 용어집 갱신 작업 상태를 확인합니다.</p>
      </div>
      <JobsPage jobs={jobs} />
    </div>
  )
}
