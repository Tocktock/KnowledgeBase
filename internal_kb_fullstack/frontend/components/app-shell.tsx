'use client'

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookMarked,
  BookOpenText,
  ChevronDown,
  Clock3,
  Home,
  Link2,
  LogIn,
  LogOut,
  Menu,
  PlusSquare,
  Search,
  Sparkles,
  UserRound,
  Workflow,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { CommandPalette } from '@/components/command-palette'
import { ThemeToggle } from '@/components/theme-toggle'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { AuthMeResponse, DocumentListResponse, UserSummary } from '@/lib/types'
import { cn, formatDate } from '@/lib/utils'
import { useUiStore } from '@/store/ui-store'

const primaryNavItems = [
  { href: '/', label: '홈', icon: Home },
  { href: '/search', label: '워크스페이스 검색', icon: Search },
  { href: '/docs', label: '문서 탐색', icon: BookOpenText },
  { href: '/glossary', label: '핵심 개념', icon: BookMarked },
]

const manageNavItems = [
  { href: '/connectors', label: '데이터 소스', icon: Link2 },
  { href: '/glossary/review', label: '지식 검수', icon: Sparkles },
  { href: '/jobs', label: '동기화 상태', icon: Workflow },
]

const contributionNavItems = [
  { href: '/new', label: '새 문서 추가', icon: PlusSquare },
]

function isNavItemActive(pathname: string, href: string) {
  if (href === '/') {
    return pathname === href
  }
  return pathname === href || pathname.startsWith(`${href}/`)
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail || detail
    } catch {
      detail = response.statusText
    }
    throw new Error(detail)
  }
  return (await response.json()) as T
}

function buildReturnTo(pathname: string, search: string) {
  return search ? `${pathname}?${search}` : pathname
}

function buildLoginHref(returnTo: string) {
  return `/login?return_to=${encodeURIComponent(returnTo)}`
}

function AccountDropdown({
  authenticated,
  loading,
  loginHref,
  loggingOut,
  onLogout,
  user,
  variant,
}: {
  authenticated: boolean
  loading: boolean
  loginHref: string
  loggingOut: boolean
  onLogout: () => void
  user: UserSummary | null
  variant: 'header' | 'sidebar'
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function handlePointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  useEffect(() => {
    setOpen(false)
  }, [authenticated, user?.id])

  if (loading) {
    return (
      <Button
        size="sm"
        variant="outline"
        disabled
        className={cn(variant === 'sidebar' ? 'w-full justify-start' : '')}
      >
        계정 확인 중
      </Button>
    )
  }

  if (!authenticated || !user) {
    return (
      <Button
        size="sm"
        variant={variant === 'header' ? 'outline' : 'default'}
        className={cn(variant === 'sidebar' ? 'w-full justify-center' : '')}
        onClick={() => window.location.assign(loginHref)}
      >
        <LogIn className="size-4" />
        로그인
      </Button>
    )
  }

  const triggerClassName =
    variant === 'header'
      ? 'min-h-9 max-w-full rounded-xl border border-neutral-200 bg-white px-2 py-1.5 text-sm text-neutral-800 hover:bg-neutral-50 sm:px-3 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100 dark:hover:bg-neutral-900'
      : 'w-full rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-left text-sm text-neutral-800 hover:bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100 dark:hover:bg-neutral-900'
  const menuClassName =
    variant === 'header'
      ? 'right-0 mt-2 w-[min(20rem,calc(100vw-2rem))]'
      : 'left-0 mt-2 w-full'

  return (
    <div ref={rootRef} className={cn('relative', variant === 'sidebar' ? 'w-full' : '')}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={variant === 'header' ? '계정 메뉴 열기' : '사이드바 계정 메뉴 열기'}
        className={cn(
          'inline-flex max-w-full items-center gap-2 transition',
          triggerClassName,
        )}
      >
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
          <UserRound className="size-4" />
        </div>
        <div className={cn('min-w-0', variant === 'header' ? 'hidden text-left sm:block' : 'flex-1')}>
          <div className="truncate font-medium">{user.name}</div>
          <div className="truncate text-xs text-neutral-500 dark:text-neutral-400">{user.email}</div>
        </div>
        <ChevronDown className={cn('size-4 text-neutral-400 transition', open ? 'rotate-180' : '')} />
      </button>

      {open ? (
        <div
          className={cn(
            'absolute top-full z-50 rounded-2xl border border-neutral-200 bg-white p-4 shadow-xl shadow-neutral-200/50 dark:border-neutral-800 dark:bg-neutral-950 dark:shadow-black/30',
            menuClassName,
          )}
        >
          <div className="space-y-1">
            <div className="text-sm font-semibold text-neutral-950 dark:text-neutral-50">{user.name}</div>
            <div className="break-all text-sm text-neutral-500 dark:text-neutral-400">{user.email}</div>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {user.current_workspace ? <Badge>{user.current_workspace.name}</Badge> : null}
            {user.current_workspace_role ? <Badge>{user.current_workspace_role}</Badge> : null}
            <Badge>{user.can_manage_workspace_connectors ? '관리 가능' : '읽기 전용'}</Badge>
          </div>

          <div className="mt-3 text-xs text-neutral-500 dark:text-neutral-400">
            최근 로그인 {formatDate(user.last_login_at)}
          </div>

          <div className="mt-4 flex gap-2">
            <Button size="sm" variant="outline" onClick={() => window.location.assign('/connectors')}>
              연결 소스
            </Button>
            <Button size="sm" variant="ghost" onClick={onLogout} disabled={loggingOut}>
              <LogOut className="size-4" />
              로그아웃
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const queryClient = useQueryClient()
  const { setCommandOpen, mobileSidebarOpen, setMobileSidebarOpen } = useUiStore()
  const [currentSearch, setCurrentSearch] = useState('')

  useEffect(() => {
    const nextSearch = window.location.search.startsWith('?')
      ? window.location.search.slice(1)
      : window.location.search
    setCurrentSearch((current) => (current === nextSearch ? current : nextSearch))
  })

  const returnTo = useMemo(() => buildReturnTo(pathname, currentSearch), [currentSearch, pathname])
  const loginHref = useMemo(() => buildLoginHref(returnTo), [returnTo])

  const authQuery = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => fetchJson<AuthMeResponse>('/api/auth/me'),
  })
  const recentDocsQuery = useQuery({
    queryKey: ['recent-documents', 12],
    queryFn: () => fetchJson<DocumentListResponse>('/api/documents?limit=12'),
    staleTime: 60_000,
  })

  const logoutMutation = useMutation({
    mutationFn: async () =>
      fetchJson<{ ok: boolean }>('/api/auth/logout', {
        method: 'POST',
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['auth-me'] }),
        queryClient.invalidateQueries({ queryKey: ['connectors'] }),
        queryClient.invalidateQueries({ queryKey: ['connectors-readiness'] }),
        queryClient.invalidateQueries({ queryKey: ['workspace-members'] }),
        queryClient.invalidateQueries({ queryKey: ['workspace-invitations'] }),
      ])
    },
  })

  const authenticated = authQuery.data?.authenticated === true
  const user = authQuery.data?.user ?? null
  const recentDocs = recentDocsQuery.data?.items ?? []

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_40%),linear-gradient(to_bottom,_rgba(255,255,255,1),_rgba(249,250,251,1))] text-neutral-900 dark:bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.1),_transparent_35%),linear-gradient(to_bottom,_rgba(10,10,10,1),_rgba(17,17,17,1))] dark:text-neutral-100">
      <CommandPalette />
      {mobileSidebarOpen ? (
        <button
          type="button"
          aria-label="사이드바 닫기"
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-neutral-950/45 lg:hidden"
        />
      ) : null}
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside
          className={cn(
            'fixed inset-y-0 left-0 z-40 w-[280px] overflow-y-auto border-r border-neutral-200 bg-white/85 p-5 backdrop-blur-xl transition-transform dark:border-neutral-800 dark:bg-neutral-950/85 lg:sticky lg:translate-x-0',
            mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <div className="mb-6 flex items-center justify-between lg:justify-start">
            <Link href="/" className="flex min-w-0 items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/25">KB</div>
              <div className="min-w-0">
                <div className="text-sm font-semibold">Internal Knowledge</div>
                <div className="text-xs text-neutral-500">Workspace Knowledge Layer</div>
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
            <Search className="size-4 shrink-0" />
            <span className="min-w-0 flex-1 truncate text-left">빠른 이동 / 검색</span>
            <Badge>⌘K</Badge>
          </button>

          <div className="mb-6 rounded-3xl border border-neutral-200 bg-white/70 p-3 dark:border-neutral-800 dark:bg-neutral-950/60">
            <div className="mb-3 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">
              <UserRound className="size-3.5" /> 계정
            </div>
            <AccountDropdown
              authenticated={authenticated}
              loading={authQuery.isLoading}
              loginHref={loginHref}
              loggingOut={logoutMutation.isPending}
              onLogout={() => logoutMutation.mutate()}
              user={user}
              variant="sidebar"
            />
            {!authenticated ? (
              <div className="mt-3 px-1 text-xs leading-6 text-neutral-500 dark:text-neutral-400">
                Google OAuth 또는 이메일/비밀번호로 로그인할 수 있습니다.
              </div>
            ) : null}
          </div>

          <nav className="space-y-6">
            <div>
              <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">Primary</div>
              <div className="space-y-1">
                {primaryNavItems.map((item) => {
                  const Icon = item.icon
                  const active = isNavItemActive(pathname, item.href)
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
                      <Icon className="size-4 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>

            {user?.can_manage_workspace_connectors ? (
              <div>
                <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">Manage</div>
                <div className="space-y-1">
                  {manageNavItems.map((item) => {
                    const Icon = item.icon
                    const active = isNavItemActive(pathname, item.href)
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
                        <Icon className="size-4 shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      </Link>
                    )
                  })}
                </div>
              </div>
            ) : null}

            {authenticated ? (
              <div>
                <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">Contribute</div>
                <div className="space-y-1">
                  {contributionNavItems.map((item) => {
                    const Icon = item.icon
                    const active = isNavItemActive(pathname, item.href)
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
                        <Icon className="size-4 shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      </Link>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </nav>

          <div className="mt-8">
            <div className="mb-3 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">
              <Clock3 className="size-3.5" /> 최근 업데이트
            </div>
            {recentDocsQuery.isLoading ? (
              <div className="px-3 py-2 text-sm text-neutral-500 dark:text-neutral-400">최근 문서를 불러오는 중입니다.</div>
            ) : recentDocs.length > 0 ? (
              <div className="space-y-1">
                {recentDocs.slice(0, 10).map((doc) => (
                  <Link
                    key={doc.id}
                    href={`/docs/${doc.slug}`}
                    className="block rounded-2xl px-3 py-2.5 transition hover:bg-neutral-100 dark:hover:bg-neutral-900"
                  >
                    <div className="line-clamp-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">{doc.title}</div>
                    <div className="line-clamp-1 text-xs text-neutral-400">/{doc.slug}</div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="px-3 py-2 text-sm text-neutral-500 dark:text-neutral-400">최근 표시할 문서가 없습니다.</div>
            )}
          </div>
        </aside>

        <div className="min-w-0">
          <header className="sticky top-0 z-30 border-b border-neutral-200 bg-white/70 backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-950/70">
            <div className="flex h-16 items-center gap-3 px-4 md:px-8">
              <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setMobileSidebarOpen(true)}>
                <Menu className="size-4" />
              </Button>
              <div className="hidden min-w-0 flex-1 text-sm text-neutral-500 line-clamp-1 dark:text-neutral-400 md:block">
                연결된 팀 지식을 검색 가능한 워크스페이스 컨텍스트로 정리합니다.
              </div>
              <AccountDropdown
                authenticated={authenticated}
                loading={authQuery.isLoading}
                loginHref={loginHref}
                loggingOut={logoutMutation.isPending}
                onLogout={() => logoutMutation.mutate()}
                user={user}
                variant="header"
              />
              <ThemeToggle />
            </div>
          </header>

          <main className="px-4 py-6 md:px-8 lg:px-10">{children}</main>
        </div>
      </div>
    </div>
  )
}
