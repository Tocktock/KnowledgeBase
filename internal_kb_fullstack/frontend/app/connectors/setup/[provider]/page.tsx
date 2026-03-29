import { Suspense } from 'react'

import { ConnectorSetupPage } from '@/components/connectors/connectors-page'

export default async function ConnectorSetupRoutePage({
  params,
  searchParams,
}: {
  params: Promise<{ provider: string }>
  searchParams: Promise<{ scope?: string; template?: string; connectionId?: string }>
}) {
  const { provider } = await params
  const { scope, template, connectionId } = await searchParams

  return (
    <Suspense
      fallback={
        <div className="rounded-3xl border border-neutral-200 bg-white/70 px-6 py-5 text-sm text-neutral-500 dark:border-neutral-800 dark:bg-neutral-950/60 dark:text-neutral-400">
          연결 설정 화면을 준비하는 중입니다.
        </div>
      }
    >
      <ConnectorSetupPage
        providerPath={provider}
        scope={scope === 'personal' ? 'personal' : 'workspace'}
        template={template ?? null}
        connectionId={connectionId ?? null}
      />
    </Suspense>
  )
}
