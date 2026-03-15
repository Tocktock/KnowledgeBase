import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn('rounded-3xl border border-neutral-200 bg-white/90 shadow-sm backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/90', className)}>
      {children}
    </div>
  )
}
