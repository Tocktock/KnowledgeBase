import { forwardRef, InputHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        'h-11 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm text-neutral-900 outline-none ring-0 placeholder:text-neutral-400 focus:border-blue-500 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100 dark:placeholder:text-neutral-600',
        className,
      )}
      {...props}
    />
  )
})
