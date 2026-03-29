import { ManageAccessGuard } from '@/components/auth/manage-access-guard'
import { JobsPage } from '@/components/jobs/jobs-page'

export default function JobsRoutePage() {
  return (
    <ManageAccessGuard
      title="동기화 상태"
      description="동기화 상태는 워크스페이스 관리자가 외부 소스의 건강 상태를 확인하는 운영 화면입니다."
    >
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">동기화 상태</h1>
          <p className="mt-2 text-sm leading-7 text-neutral-500">문서 동기화, 개념 갱신, 실패 작업을 점검하고 조치가 필요한 소스를 찾습니다.</p>
        </div>
        <JobsPage />
      </div>
    </ManageAccessGuard>
  )
}
