import Link from 'next/link'
import React, { type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { headingId } from '@/lib/utils'
import { preprocessWikiMarkdown } from '@/lib/wiki'

function textFromChildren(children: ReactNode): string {
  if (typeof children === 'string') return children
  if (typeof children === 'number') return String(children)
  if (Array.isArray(children)) return children.map(textFromChildren).join('')
  if (React.isValidElement(children)) return textFromChildren((children.props as { children?: ReactNode }).children)
  return ''
}

function Heading({
  as: Comp,
  children,
}: {
  as: 'h1' | 'h2' | 'h3' | 'h4'
  children: ReactNode
}) {
  const text = textFromChildren(children)
  const id = headingId(text)
  const className = {
    h1: 'mt-10 scroll-mt-24 text-4xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50',
    h2: 'mt-9 scroll-mt-24 text-2xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50',
    h3: 'mt-8 scroll-mt-24 text-xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100',
    h4: 'mt-6 scroll-mt-24 text-lg font-semibold text-neutral-900 dark:text-neutral-100',
  }[Comp]

  return (
    <Comp id={id} className={className}>
      {children}
    </Comp>
  )
}

export function MarkdownRenderer({ markdown }: { markdown: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <Heading as="h1">{children}</Heading>,
        h2: ({ children }) => <Heading as="h2">{children}</Heading>,
        h3: ({ children }) => <Heading as="h3">{children}</Heading>,
        h4: ({ children }) => <Heading as="h4">{children}</Heading>,
        p: ({ children }) => <p className="my-4 text-[15px] leading-8 text-neutral-700 dark:text-neutral-300">{children}</p>,
        a: ({ href = '', children }) => {
          const internal = href.startsWith('/docs/')
          if (internal) {
            return (
              <Link href={href} className="font-medium text-blue-600 underline decoration-blue-200 underline-offset-4 hover:text-blue-500 dark:text-blue-400 dark:decoration-blue-900">
                {children}
              </Link>
            )
          }
          return (
            <a href={href} target="_blank" rel="noreferrer" className="font-medium text-blue-600 underline decoration-blue-200 underline-offset-4 hover:text-blue-500 dark:text-blue-400 dark:decoration-blue-900">
              {children}
            </a>
          )
        },
        blockquote: ({ children }) => (
          <blockquote className="my-6 rounded-r-2xl border-l-4 border-blue-500 bg-blue-50/70 px-4 py-3 text-sm leading-7 text-neutral-700 dark:bg-blue-950/20 dark:text-neutral-300">
            {children}
          </blockquote>
        ),
        ul: ({ children }) => <ul className="my-4 list-disc space-y-2 pl-6 text-[15px] leading-8 text-neutral-700 dark:text-neutral-300">{children}</ul>,
        ol: ({ children }) => <ol className="my-4 list-decimal space-y-2 pl-6 text-[15px] leading-8 text-neutral-700 dark:text-neutral-300">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        hr: () => <hr className="my-8 border-neutral-200 dark:border-neutral-800" />,
        code: ({ className, children }) => {
          const inline = !className
          if (inline) {
            return <code className="rounded-md bg-neutral-100 px-1.5 py-1 text-[0.9em] text-pink-600 dark:bg-neutral-900 dark:text-pink-400">{children}</code>
          }
          return <code className="block text-sm leading-7 text-neutral-200">{children}</code>
        },
        pre: ({ children }) => (
          <pre className="my-6 overflow-x-auto rounded-2xl border border-neutral-800 bg-neutral-950 p-4 text-sm leading-7 shadow-inner">{children}</pre>
        ),
        table: ({ children }) => <div className="my-6 overflow-x-auto"><table className="min-w-full border-collapse overflow-hidden rounded-2xl border border-neutral-200 dark:border-neutral-800">{children}</table></div>,
        thead: ({ children }) => <thead className="bg-neutral-50 dark:bg-neutral-900">{children}</thead>,
        th: ({ children }) => <th className="border-b border-neutral-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">{children}</th>,
        td: ({ children }) => <td className="border-b border-neutral-200 px-4 py-3 text-sm text-neutral-700 dark:border-neutral-800 dark:text-neutral-300">{children}</td>,
      }}
    >
      {preprocessWikiMarkdown(markdown)}
    </ReactMarkdown>
  )
}
