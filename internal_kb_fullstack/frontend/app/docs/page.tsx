import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { getDocsDomainPreset } from '@/lib/document-domains'
import { formatDocTypeLabel } from '@/lib/utils'
import { DocsExplorer } from '@/components/docs/docs-explorer'

export const dynamic = 'force-dynamic'

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
            {preset?.docsSubtitle ?? '팀, 타입, 본문 기준으로 문서를 좁혀가며 찾을 수 있습니다.'}
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
      <DocsExplorer key={preset?.key ?? 'all'} preset={preset ?? undefined} />
    </div>
  )
}
