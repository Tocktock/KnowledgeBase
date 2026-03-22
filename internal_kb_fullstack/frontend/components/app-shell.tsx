'use client'

import type { ReactNode } from 'react'
import { BookMarked, BookOpenText, Clock3, Home, Menu, PlusSquare, Search, Sparkles, Workflow } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { CommandPalette } from '@/components/command-palette'
import { ThemeToggle } from '@/components/theme-toggle'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { DocumentListItem } from '@/lib/types'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/store/ui-store'

const navItems = [
  { href: '/', label: '홈', icon: Home },
  { href: '/search', label: '시맨틱 검색', icon: Search },
  { href: '/docs', label: '문서 탐색', icon: BookOpenText },
  { href: '/glossary', label: '용어집', icon: BookMarked },
  { href: '/glossary/review', label: '리뷰 스튜디오', icon: Sparkles },
  { href: '/new', label: '새 문서', icon: PlusSquare },
  { href: '/jobs', label: '인덱싱 작업', icon: Workflow },
]

export function AppShell({
  recentDocs,
  children,
}: {
  recentDocs: DocumentListItem[]
  children: ReactNode
}) {
  const pathname = usePathname()
  const { setCommandOpen, mobileSidebarOpen, setMobileSidebarOpen } = useUiStore()

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_40%),linear-gradient(to_bottom,_rgba(255,255,255,1),_rgba(249,250,251,1))] text-neutral-900 dark:bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.1),_transparent_35%),linear-gradient(to_bottom,_rgba(10,10,10,1),_rgba(17,17,17,1))] dark:text-neutral-100">
      <CommandPalette />
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside
          className={cn(
            'fixed inset-y-0 left-0 z-40 w-[280px] border-r border-neutral-200 bg-white/85 p-5 backdrop-blur-xl transition-transform dark:border-neutral-800 dark:bg-neutral-950/85 lg:sticky lg:translate-x-0',
            mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <div className="mb-6 flex items-center justify-between lg:justify-start">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/25">KB</div>
              <div>
                <div className="text-sm font-semibold">Internal Knowledge</div>
                <div className="text-xs text-neutral-500">Notion × Wiki Fusion</div>
              </div>
            </Link>
            <Button variant="ghost" size="sm" onClick={() => setMobileSidebarOpen(false)} className="lg:hidden">
              닫기
            </Button>
          </div>

          <button
            onClick={() => setCommandOpen(true)}
            className="mb-6 flex h-11 w-full items-center gap-3 rounded-2xl border border-neutral-200 bg-neutral-50 px-4 text-sm text-neutral-500 transition hover:border-blue-300 hover:text-neutral-900 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400 dark:hover:border-blue-700 dark:hover:text-neutral-100"
          >
            <Search className="size-4" />
            <span className="flex-1 text-left">빠른 이동 / 검색</span>
            <Badge>⌘K</Badge>
          </button>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition',
                    active
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                      : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-300 dark:hover:bg-neutral-900 dark:hover:text-neutral-50',
                  )}
                >
                  <Icon className="size-4" />
                  {item.label}
                </Link>
              )
            })}
          </nav>

          <div className="mt-8">
            <div className="mb-3 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">
              <Clock3 className="size-3.5" /> 최근 업데이트
            </div>
            <div className="space-y-1">
              {recentDocs.slice(0, 10).map((doc) => (
                <Link
                  key={doc.id}
                  href={`/docs/${doc.slug}`}
                  className="block rounded-2xl px-3 py-2.5 transition hover:bg-neutral-100 dark:hover:bg-neutral-900"
                >
                  <div className="line-clamp-1 text-sm font-medium text-neutral-800 dark:text-neutral-200">{doc.title}</div>
                  <div className="line-clamp-1 text-xs text-neutral-400">/{doc.slug}</div>
                </Link>
              ))}
            </div>
          </div>
        </aside>

        <div className="min-w-0">
          <header className="sticky top-0 z-30 border-b border-neutral-200 bg-white/70 backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-950/70">
            <div className="flex h-16 items-center gap-3 px-4 md:px-8">
              <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setMobileSidebarOpen(true)}>
                <Menu className="size-4" />
              </Button>
              <div className="flex-1 text-sm text-neutral-500 dark:text-neutral-400">
                깔끔한 작성 경험은 노션처럼, 문서 연결과 탐색은 위키처럼.
              </div>
              <ThemeToggle />
            </div>
          </header>

          <main className="px-4 py-6 md:px-8 lg:px-10">{children}</main>
        </div>
      </div>
    </div>
  )
}
