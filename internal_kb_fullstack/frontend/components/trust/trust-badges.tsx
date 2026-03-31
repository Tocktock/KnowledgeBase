import { ExternalLink } from 'lucide-react'
import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { getDisplaySourceUrl, getOutboundSourceUrl } from '@/lib/source-urls'
import type { TrustSummary } from '@/lib/types'
import { formatAuthorityKindLabel, formatFreshnessStateLabel, formatTrustSourceLabel } from '@/lib/utils'

export function TrustBadges({
  trust,
  showEvidenceCount = true,
  showSourceLink = false,
}: {
  trust: TrustSummary
  showEvidenceCount?: boolean
  showSourceLink?: boolean
}) {
  const sourceUrl = getDisplaySourceUrl(trust.source_url)
  const outboundSourceUrl = getOutboundSourceUrl(sourceUrl)

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
      <Badge>{formatTrustSourceLabel(trust.source_label)}</Badge>
      <Badge>{formatFreshnessStateLabel(trust.freshness_state)}</Badge>
      <Badge>{formatAuthorityKindLabel(trust.authority_kind)}</Badge>
      {showEvidenceCount ? <Badge>근거 {trust.evidence_count}건</Badge> : null}
      {showSourceLink && sourceUrl ? (
        outboundSourceUrl ? (
          <Link
            href={outboundSourceUrl}
            target="_blank"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-500 dark:text-blue-400"
          >
            원본 <ExternalLink className="size-3.5" />
          </Link>
        ) : (
          <span className="max-w-full break-all text-neutral-500 dark:text-neutral-400">출처 {sourceUrl}</span>
        )
      ) : null}
    </div>
  )
}
