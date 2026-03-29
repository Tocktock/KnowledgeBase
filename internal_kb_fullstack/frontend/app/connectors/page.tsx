import { Suspense } from 'react'

import { ConnectorsPage } from '@/components/connectors/connectors-page'

export default function ConnectorsRoutePage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-3xl border border-neutral-200 bg-white/70 px-6 py-5 text-sm text-neutral-500 dark:border-neutral-800 dark:bg-neutral-950/60 dark:text-neutral-400">
          데이터 소스 화면을 준비하는 중입니다.
        </div>
      }
    >
      <ConnectorsPage />
    </Suspense>
  )
}
