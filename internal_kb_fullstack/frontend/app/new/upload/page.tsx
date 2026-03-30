import { WorkspaceMemberGuard } from '@/components/auth/manage-access-guard'
import { DocumentEditorWorkspace } from '@/components/editor/document-editor'

export default function NewUploadDocumentPage() {
  return (
    <WorkspaceMemberGuard
      title="파일 업로드"
      description="파일 업로드는 활성 워크스페이스 멤버만 사용할 수 있습니다."
    >
      <DocumentEditorWorkspace flow="upload" />
    </WorkspaceMemberGuard>
  )
}
