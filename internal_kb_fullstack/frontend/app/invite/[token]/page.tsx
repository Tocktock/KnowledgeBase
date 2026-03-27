'use client'

import { LoaderCircle } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'

import type { AuthMeResponse, WorkspaceInvitationAcceptResponse } from '@/lib/types'

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || '요청에 실패했습니다.')
  }
  return (await response.json()) as T
}

export default function InviteAcceptPage() {
  const router = useRouter()
  const params = useParams<{ token: string }>()
  const token = typeof params?.token === 'string' ? params.token : ''
  const [message, setMessage] = useState('초대 링크를 확인하고 있습니다.')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function run() {
      try {
        if (!token) {
          throw new Error('초대 토큰을 확인하지 못했습니다.')
        }
        const auth = await fetchJson<AuthMeResponse>('/api/auth/me')
        if (!auth.authenticated) {
          window.location.replace(`/login?invite_token=${encodeURIComponent(token)}`)
          return
        }
        setMessage('워크스페이스 초대를 수락하는 중입니다.')
        await fetchJson<WorkspaceInvitationAcceptResponse>(`/api/workspace/invitations/${encodeURIComponent(token)}/accept`, {
          method: 'POST',
        })
        if (!cancelled) {
          router.replace('/connectors')
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : '초대를 처리하지 못했습니다.')
        }
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [router, token])

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-xl items-center justify-center px-6">
      <div className="w-full rounded-3xl border border-neutral-200 bg-white p-8 text-center shadow-sm dark:border-neutral-800 dark:bg-neutral-950">
        {error ? (
          <>
            <div className="text-lg font-semibold text-neutral-950 dark:text-neutral-50">초대를 수락하지 못했습니다.</div>
            <div className="mt-3 text-sm leading-7 text-red-600 dark:text-red-400">{error}</div>
          </>
        ) : (
          <>
            <div className="flex justify-center">
              <LoaderCircle className="size-6 animate-spin text-blue-500" />
            </div>
            <div className="mt-4 text-lg font-semibold text-neutral-950 dark:text-neutral-50">워크스페이스 참여 준비 중</div>
            <div className="mt-3 text-sm leading-7 text-neutral-500 dark:text-neutral-400">{message}</div>
          </>
        )}
      </div>
    </div>
  )
}
