import { WorkspaceMemberGuard } from '@/components/auth/manage-access-guard'
import { DocumentModeChooserPage } from '@/components/editor/document-editor'

export default function NewDocumentPage() {
  return (
    <WorkspaceMemberGuard
      title="새 문서 작성"
      description="문서 작성과 업로드는 활성 워크스페이스 멤버만 사용할 수 있습니다."
    >
      <DocumentModeChooserPage />
    </WorkspaceMemberGuard>
  )
}
