import { ManageAccessGuard } from '@/components/auth/manage-access-guard'
import { GlossaryReviewPage } from '@/components/glossary/glossary-review-page'

export default function GlossaryReviewRoutePage() {
  return (
    <ManageAccessGuard
      title="지식 검수"
      description="지식 검수는 워크스페이스 관리자가 개념 품질과 대표 문서를 조정하는 운영 화면입니다."
    >
      <GlossaryReviewPage />
    </ManageAccessGuard>
  )
}
