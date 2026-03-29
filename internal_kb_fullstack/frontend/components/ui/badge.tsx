import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export function Badge({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex max-w-full min-w-0 items-center rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-center text-xs font-medium leading-5 text-neutral-700 break-words whitespace-normal dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300',
        className,
      )}
    >
      {children}
    </span>
  )
}
