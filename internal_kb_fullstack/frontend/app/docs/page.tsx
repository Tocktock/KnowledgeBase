import { DocsExplorer } from '@/components/docs/docs-explorer'

export const dynamic = 'force-dynamic'

export default function DocsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">문서 탐색</h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">팀, 타입, 본문 기준으로 문서를 좁혀가며 찾을 수 있습니다.</p>
      </div>
      <DocsExplorer />
    </div>
  )
}
