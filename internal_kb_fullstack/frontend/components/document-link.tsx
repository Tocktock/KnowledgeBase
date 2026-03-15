import Link from 'next/link'

import { cn } from '@/lib/utils'

export function DocumentLink({
  slug,
  title,
  className,
}: {
  slug: string
  title: string
  className?: string
}) {
  return (
    <Link
      href={`/docs/${slug}`}
      className={cn(
        'text-blue-600 underline decoration-blue-200 underline-offset-4 hover:text-blue-500 dark:text-blue-400 dark:decoration-blue-800',
        className,
      )}
    >
      {title}
    </Link>
  )
}
