import { WorkspaceMemberGuard } from '@/components/auth/manage-access-guard'
import { DocumentEditorWorkspace } from '@/components/editor/document-editor'

export default function NewManualDocumentPage() {
  return (
    <WorkspaceMemberGuard
      title="직접 작성"
      description="직접 작성은 활성 워크스페이스 멤버만 사용할 수 있습니다."
    >
      <DocumentEditorWorkspace flow="manual" />
    </WorkspaceMemberGuard>
  )
}
