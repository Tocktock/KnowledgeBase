import { WorkspaceMemberGuard } from '@/components/auth/manage-access-guard'
import { DocumentEditorWorkspace } from '@/components/editor/document-editor'

export default function NewDefinitionDocumentPage() {
  return (
    <WorkspaceMemberGuard
      title="정의 초안 생성"
      description="정의 초안 생성은 활성 워크스페이스 멤버만 사용할 수 있습니다."
    >
      <DocumentEditorWorkspace flow="definition" />
    </WorkspaceMemberGuard>
  )
}
