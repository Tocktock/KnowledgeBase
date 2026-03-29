import { ButtonHTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

type Variant = 'default' | 'secondary' | 'ghost' | 'outline' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const variants: Record<Variant, string> = {
  default: 'bg-neutral-900 text-white shadow-sm hover:bg-neutral-800 dark:bg-white dark:text-neutral-950 dark:hover:bg-neutral-200',
  secondary: 'bg-blue-600 text-white shadow-sm hover:bg-blue-500',
  ghost: 'bg-transparent text-neutral-700 hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-900',
  outline: 'border border-neutral-200 bg-white text-neutral-800 hover:bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100 dark:hover:bg-neutral-900',
  danger: 'bg-red-600 text-white hover:bg-red-500',
}

const sizes: Record<Size, string> = {
  sm: 'min-h-8 rounded-lg px-3 py-1.5 text-sm',
  md: 'min-h-10 rounded-xl px-4 py-2 text-sm',
  lg: 'min-h-11 rounded-xl px-5 py-2.5 text-base',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = 'default', size = 'md', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(
        'inline-flex max-w-full items-center justify-center gap-2 text-center font-medium leading-5 whitespace-normal transition disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  )
})
