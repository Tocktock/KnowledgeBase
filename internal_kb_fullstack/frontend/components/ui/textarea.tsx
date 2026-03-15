import { forwardRef, TextareaHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        'min-h-[160px] w-full rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-900 outline-none placeholder:text-neutral-400 focus:border-blue-500 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100 dark:placeholder:text-neutral-600',
        className,
      )}
      {...props}
    />
  )
})
