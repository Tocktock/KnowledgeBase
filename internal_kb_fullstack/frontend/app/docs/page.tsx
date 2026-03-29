import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { getDocsDomainPreset } from '@/lib/document-domains'
import { formatDocTypeLabel } from '@/lib/utils'
import { DocsExplorer } from '@/components/docs/docs-explorer'

type DocsPageProps = {
  searchParams?: Promise<{
    domain?: string | string[]
  }>
}

export default async function DocsPage({ searchParams }: DocsPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined
  const preset = getDocsDomainPreset(resolvedSearchParams?.domain)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">
            {preset?.docsTitle ?? '문서 탐색'}
          </h1>
          <p className="mt-2 text-sm leading-7 text-neutral-500">
            {preset?.docsSubtitle ?? '연결된 외부 자료와 내부 문서를 함께 살피면서, 어떤 정보가 최신이고 신뢰 가능한지 바로 확인할 수 있습니다.'}
          </p>
          {preset ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge>{preset.badge}</Badge>
              {preset.docTypes.map((docType) => (
                <Badge key={docType}>{formatDocTypeLabel(docType)}</Badge>
              ))}
            </div>
          ) : null}
        </div>
        {preset ? (
          <Link
            href="/docs"
            className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
          >
            전체 문서 보기
          </Link>
        ) : null}
      </div>
      {!preset ? (
        <div className="rounded-3xl border border-neutral-200 bg-white/70 px-5 py-4 text-sm leading-7 text-neutral-600 dark:border-neutral-800 dark:bg-neutral-950/60 dark:text-neutral-400">
          워크스페이스 문서는 Google Drive, Notion, 직접 작성한 문서가 함께 쌓이는 지식 레이어입니다. 문서 카드에서 출처와 최신성을 먼저 확인한 뒤 상세로 들어가세요.
        </div>
      ) : null}
      <DocsExplorer key={preset?.key ?? 'all'} preset={preset ?? undefined} />
    </div>
  )
}
