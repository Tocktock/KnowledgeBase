'use client'

import { useQuery } from '@tanstack/react-query'
import { Lock, ShieldCheck } from 'lucide-react'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { AuthMeResponse } from '@/lib/types'

async function fetchAuthMe() {
  const response = await fetch('/api/auth/me', { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('로그인 상태를 확인하지 못했습니다.')
  }
  return (await response.json()) as AuthMeResponse
}

export function ManageAccessGuard({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  const pathname = usePathname()
  const authQuery = useQuery({
    queryKey: ['auth-me', 'manage-access'],
    queryFn: fetchAuthMe,
  })

  if (authQuery.isLoading) {
    return (
      <Card className="p-6 text-sm text-neutral-500">
        {title} 접근 권한을 확인하는 중입니다.
      </Card>
    )
  }

  if (authQuery.isError) {
    return (
      <Card className="p-6 text-sm text-red-600 dark:text-red-400">
        {authQuery.error instanceof Error ? authQuery.error.message : '접근 권한을 확인하지 못했습니다.'}
      </Card>
    )
  }

  const authenticated = authQuery.data?.authenticated === true
  const user = authQuery.data?.user ?? null

  if (!authenticated || !user) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          <Lock className="size-4 text-blue-500" /> {title}
        </div>
        <p className="mt-3 text-sm leading-7 text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={() => window.location.assign(`/login?return_to=${encodeURIComponent(pathname)}`)}>
            로그인하기
          </Button>
          <Button variant="outline" onClick={() => window.location.assign('/search')}>
            워크스페이스 검색으로 이동
          </Button>
        </div>
      </Card>
    )
  }

  if (!user.can_manage_workspace_connectors) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          <ShieldCheck className="size-4 text-blue-500" /> 관리자 전용 화면
        </div>
        <p className="mt-3 text-sm leading-7 text-neutral-500 dark:text-neutral-400">
          {title}는 워크스페이스 관리자만 운영합니다. 구성원은 검색, 문서 탐색, 핵심 개념 화면에서 바로 지식을 소비하면 됩니다.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {user.current_workspace ? <Badge>{user.current_workspace.name}</Badge> : null}
          {user.current_workspace_role ? <Badge>{user.current_workspace_role}</Badge> : null}
          <Badge>읽기 전용 계정</Badge>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={() => window.location.assign('/search')}>워크스페이스 검색</Button>
          <Button variant="outline" onClick={() => window.location.assign('/docs')}>
            문서 탐색
          </Button>
        </div>
      </Card>
    )
  }

  return <>{children}</>
}
