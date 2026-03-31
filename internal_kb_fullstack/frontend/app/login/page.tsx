'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Link2, LoaderCircle, Lock, ShieldCheck } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { Suspense } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type {
  AuthMeResponse,
  AuthSessionResponse,
  PasswordResetPreviewResponse,
  WorkspaceInvitationPreviewResponse,
} from '@/lib/types'
import { coerceInternalPath } from '@/lib/internal-paths'
import { formatDate } from '@/lib/utils'

function normalizeAuthErrorMessage(message: string | null | undefined) {
  if (!message) return '요청에 실패했습니다.'
  if (message === 'Workspace invitation not found.') return '초대 링크를 찾을 수 없습니다.'
  if (message === 'Password reset token not found.') return '비밀번호 재설정 링크를 찾을 수 없습니다.'
  if (message === 'Password reset token has already been used.') return '이 비밀번호 재설정 링크는 이미 사용되었습니다.'
  if (message === 'Password reset token has expired.') return '이 비밀번호 재설정 링크는 만료되었습니다.'
  if (message === 'Password reset user not found.') return '비밀번호를 재설정할 계정을 찾을 수 없습니다.'
  return message
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  const bodyText = await response.text()
  if (!response.ok) {
    if (bodyText) {
      let parsedMessage: string | null = null
      try {
        const parsed = JSON.parse(bodyText) as { detail?: string; message?: string; error?: string }
        parsedMessage = parsed.detail ?? parsed.message ?? parsed.error ?? null
      } catch {}
      throw new Error(normalizeAuthErrorMessage(parsedMessage ?? bodyText))
    }
    throw new Error('요청에 실패했습니다.')
  }
  return bodyText ? (JSON.parse(bodyText) as T) : (null as T)
}

function providerPath(value: string | null) {
  if (value === 'notion') return 'notion'
  if (value === 'github') return 'github'
  return 'google-drive'
}

function authErrorMessage(value: string | null) {
  if (value === 'login_unavailable') return '관리자가 아직 로그인 또는 연결 기능을 준비하지 않았습니다.'
  return null
}

function LoginPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()

  const returnTo = coerceInternalPath(searchParams.get('return_to'), '/connectors')
  const postAuthAction = searchParams.get('post_auth_action')
  const ownerScope = searchParams.get('owner_scope')
  const provider = searchParams.get('provider')
  const inviteToken = searchParams.get('invite_token')
  const resetToken = searchParams.get('reset_token')
  const initialError = authErrorMessage(searchParams.get('auth_error'))

  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(initialError)

  const authQuery = useQuery({
    queryKey: ['auth-me', 'login-page'],
    queryFn: () => fetchJson<AuthMeResponse>('/api/auth/me'),
  })

  const invitationPreviewQuery = useQuery({
    queryKey: ['workspace-invitation-preview', inviteToken],
    queryFn: () =>
      fetchJson<WorkspaceInvitationPreviewResponse>(
        `/api/workspace/invitations/${encodeURIComponent(inviteToken ?? '')}/preview`,
      ),
    enabled: Boolean(inviteToken),
    retry: false,
  })

  const resetPreviewQuery = useQuery({
    queryKey: ['password-reset-preview', resetToken],
    queryFn: () =>
      fetchJson<PasswordResetPreviewResponse>(`/api/auth/password/reset/${encodeURIComponent(resetToken ?? '')}`),
    enabled: Boolean(resetToken),
    retry: false,
  })

  const googleHref = useMemo(() => {
    const search = new URLSearchParams()
    if (inviteToken) {
      search.set('return_to', `/invite/${inviteToken}`)
    } else {
      search.set('return_to', returnTo)
      if (postAuthAction) search.set('post_auth_action', postAuthAction)
      if (ownerScope) search.set('owner_scope', ownerScope)
      if (provider) search.set('provider', provider)
    }
    return `/api/auth/google/start?${search.toString()}`
  }, [inviteToken, ownerScope, postAuthAction, provider, returnTo])

  useEffect(() => {
    if (authQuery.data?.authenticated !== true) return
    if (resetToken) return
    if (inviteToken) {
      router.replace(`/invite/${inviteToken}`)
      return
    }
    if (postAuthAction === 'connect_provider') {
      const search = new URLSearchParams({
        scope: ownerScope ?? 'workspace',
        return_to: returnTo,
      })
      window.location.replace(`/api/connectors/${providerPath(provider)}/oauth/start?${search.toString()}`)
      return
    }
    router.replace(returnTo)
  }, [authQuery.data, inviteToken, ownerScope, postAuthAction, provider, resetToken, returnTo, router])

  const sessionSuccess = async (payload: AuthSessionResponse) => {
    queryClient.setQueryData<AuthMeResponse>(['auth-me'], {
      authenticated: true,
      user: payload.user,
    })
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['auth-me'] }),
      queryClient.invalidateQueries({ queryKey: ['workspace-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['connectors'] }),
      queryClient.invalidateQueries({ queryKey: ['connectors-readiness'] }),
      queryClient.invalidateQueries({ queryKey: ['workspace-members'] }),
      queryClient.invalidateQueries({ queryKey: ['workspace-invitations'] }),
    ])
    router.replace(coerceInternalPath(payload.redirect_to, '/connectors'))
    router.refresh()
  }

  const passwordLoginMutation = useMutation({
    mutationFn: async () =>
      fetchJson<AuthSessionResponse>('/api/auth/password/login', {
        method: 'POST',
        body: JSON.stringify({
          email: invitationPreviewQuery.data?.invited_email ?? email,
          password,
          return_to: returnTo,
          post_auth_action: postAuthAction,
          owner_scope: ownerScope,
          provider,
          invite_token: inviteToken,
        }),
      }),
    onSuccess: sessionSuccess,
    onError: (error) => setErrorMessage(error instanceof Error ? error.message : '로그인에 실패했습니다.'),
  })

  const passwordSignupMutation = useMutation({
    mutationFn: async () =>
      fetchJson<AuthSessionResponse>('/api/auth/password/invite-signup', {
        method: 'POST',
        body: JSON.stringify({
          invite_token: inviteToken,
          name,
          password,
          return_to: returnTo,
          post_auth_action: postAuthAction,
          owner_scope: ownerScope,
          provider,
        }),
      }),
    onSuccess: sessionSuccess,
    onError: (error) => setErrorMessage(error instanceof Error ? error.message : '계정을 만들지 못했습니다.'),
  })

  const passwordResetMutation = useMutation({
    mutationFn: async () =>
      fetchJson<AuthSessionResponse>(`/api/auth/password/reset/${encodeURIComponent(resetToken ?? '')}`, {
        method: 'POST',
        body: JSON.stringify({
          password,
          return_to: returnTo,
          post_auth_action: postAuthAction,
          owner_scope: ownerScope,
          provider,
        }),
      }),
    onSuccess: sessionSuccess,
    onError: (error) => setErrorMessage(error instanceof Error ? error.message : '비밀번호를 재설정하지 못했습니다.'),
  })

  const previewLoading = invitationPreviewQuery.isLoading || resetPreviewQuery.isLoading || authQuery.isLoading
  const invitePreview = invitationPreviewQuery.data
  const resetPreview = resetPreviewQuery.data
  const inviteMode = Boolean(inviteToken) && !resetToken
  const resetMode = Boolean(resetToken)
  const inviteRequiresSignup = inviteMode && invitePreview?.local_password_exists === false
  const inviteRequiresLogin = inviteMode && invitePreview?.local_password_exists === true
  const busy =
    passwordLoginMutation.isPending ||
    passwordSignupMutation.isPending ||
    passwordResetMutation.isPending

  useEffect(() => {
    if (invitationPreviewQuery.error instanceof Error) {
      setErrorMessage(invitationPreviewQuery.error.message)
      return
    }
    if (resetPreviewQuery.error instanceof Error) {
      setErrorMessage(resetPreviewQuery.error.message)
    }
  }, [invitationPreviewQuery.error, resetPreviewQuery.error])

  function ensurePasswordsMatch() {
    if (!password.trim()) {
      setErrorMessage('비밀번호를 입력해 주세요.')
      return false
    }
    if ((inviteRequiresSignup || resetMode) && !passwordConfirm.trim()) {
      setErrorMessage('비밀번호 확인을 입력해 주세요.')
      return false
    }
    if ((inviteRequiresSignup || resetMode) && password !== passwordConfirm) {
      setErrorMessage('비밀번호 확인이 일치하지 않습니다.')
      return false
    }
    return true
  }

  async function handleSubmit() {
    setErrorMessage(null)
    if (!ensurePasswordsMatch()) return
    if (resetMode) {
      await passwordResetMutation.mutateAsync()
      return
    }
    if (inviteRequiresSignup) {
      if (!name.trim()) {
        setErrorMessage('이름을 입력해 주세요.')
        return
      }
      await passwordSignupMutation.mutateAsync()
      return
    }
    if (!(inviteRequiresLogin || email.trim())) {
      setErrorMessage('이메일을 입력해 주세요.')
      return
    }
    await passwordLoginMutation.mutateAsync()
  }

  const title = resetMode
    ? '비밀번호 재설정'
    : inviteRequiresSignup
      ? '초대받은 계정 만들기'
      : '로그인'

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-5xl items-center justify-center">
      <div className="grid w-full gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="p-6">
          <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            <Link2 className="size-4 text-blue-500" /> Workspace Knowledge Layer
          </div>
	          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">{title}</h1>
	          <p className="mt-3 text-sm leading-7 text-neutral-500 dark:text-neutral-400">
	            워크스페이스 지식 레이어에 들어가는 단일 로그인 화면입니다. 표준 로그인은 Google 계정으로 진행하고, 초대된 사용자는 이메일/비밀번호 로컬 계정도 사용할 수 있습니다.
	          </p>

          {previewLoading ? (
            <div className="mt-6 flex items-center gap-2 text-sm text-neutral-500">
              <LoaderCircle className="size-4 animate-spin" /> 로그인 상태와 초대 정보를 확인하는 중입니다.
            </div>
          ) : null}

          {errorMessage ? (
            <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
              {errorMessage}
            </div>
          ) : null}

          {invitePreview ? (
            <div className="mt-6 rounded-3xl border border-neutral-200 p-5 dark:border-neutral-800">
              <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                <ShieldCheck className="size-4 text-blue-500" /> 초대된 워크스페이스
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge>{invitePreview.workspace.name}</Badge>
                <Badge>{invitePreview.role}</Badge>
                <Badge>{invitePreview.invited_email}</Badge>
                <Badge>{invitePreview.local_password_exists ? '로컬 로그인 가능' : '로컬 계정 생성 필요'}</Badge>
              </div>
              <div className="mt-3 text-sm text-neutral-500">
                만료 {formatDate(invitePreview.expires_at)}
                {invitePreview.accepted_at ? ` · 이미 수락됨 ${formatDate(invitePreview.accepted_at)}` : ''}
              </div>
              <div className="mt-2 text-sm text-neutral-500">초대 링크의 이메일과 로그인 이메일이 반드시 일치해야 합니다.</div>
            </div>
          ) : null}

          {resetPreview ? (
            <div className="mt-6 rounded-3xl border border-neutral-200 p-5 dark:border-neutral-800">
              <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                <KeyRound className="size-4 text-blue-500" /> 비밀번호 재설정 링크
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge>{resetPreview.email}</Badge>
                <Badge>만료 {formatDate(resetPreview.expires_at)}</Badge>
                {resetPreview.used_at ? <Badge>이미 사용됨</Badge> : null}
              </div>
              <div className="mt-2 text-sm text-neutral-500">링크가 만료되었거나 이미 사용되었다면 워크스페이스 관리자에게 새 링크를 요청해 주세요.</div>
            </div>
          ) : null}

	          {!resetMode ? (
	            <div className="mt-6 rounded-3xl border border-neutral-200 p-5 dark:border-neutral-800">
	              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">Google로 계속</div>
	              <div className="mt-2 text-sm text-neutral-500">
	                회사 Google 계정이 있다면 이 경로가 기본 방식입니다. 로그인 뒤에는 원래 보던 검색, 문서, 데이터 소스 연결 흐름으로 자동 복귀합니다.
	              </div>
	              <Button className="mt-4" onClick={() => window.location.assign(googleHref)}>
	                Google로 계속
              </Button>
            </div>
          ) : null}
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            <Lock className="size-4 text-blue-500" /> 이메일 / 비밀번호
          </div>
	          <div className="mt-2 text-sm text-neutral-500">
	            {resetMode
	              ? '관리자가 전달한 링크로만 비밀번호를 다시 설정할 수 있습니다.'
	              : inviteRequiresSignup
	                ? '초대 링크가 있을 때만 로컬 계정을 만들 수 있습니다. 공개 회원가입은 지원하지 않습니다.'
	                : '이미 비밀번호가 설정된 초대 계정으로 로그인합니다. 비밀번호 재설정은 관리자 링크가 필요합니다.'}
	          </div>

          <form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault()
              void handleSubmit()
            }}
          >
            <div className="space-y-4">
            {!inviteRequiresSignup && !inviteRequiresLogin && !resetMode ? (
              <label className="block space-y-2 text-sm">
                <div className="font-medium text-neutral-700 dark:text-neutral-300">이메일</div>
                <Input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  disabled={busy}
                />
              </label>
            ) : null}

            {inviteMode ? (
              <label className="block space-y-2 text-sm">
                <div className="font-medium text-neutral-700 dark:text-neutral-300">초대된 이메일</div>
                <Input
                  id="invite-email"
                  name="invite_email"
                  autoComplete="email"
                  value={invitePreview?.invited_email ?? ''}
                  disabled
                />
              </label>
            ) : null}

            {inviteRequiresSignup ? (
              <label className="block space-y-2 text-sm">
                <div className="font-medium text-neutral-700 dark:text-neutral-300">이름</div>
                <Input
                  id="signup-name"
                  name="name"
                  autoComplete="name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="표시 이름"
                  disabled={busy}
                />
              </label>
            ) : null}

            <label className="block space-y-2 text-sm">
              <div className="font-medium text-neutral-700 dark:text-neutral-300">
                {resetMode ? '새 비밀번호' : '비밀번호'}
              </div>
              <Input
                id="login-password"
                name="password"
                type="password"
                autoComplete={resetMode ? 'new-password' : inviteRequiresSignup ? 'new-password' : 'current-password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="8자 이상"
                disabled={busy}
              />
            </label>

            {(inviteRequiresSignup || resetMode) ? (
              <label className="block space-y-2 text-sm">
                <div className="font-medium text-neutral-700 dark:text-neutral-300">비밀번호 확인</div>
                <Input
                  id="login-password-confirm"
                  name="password_confirm"
                  type="password"
                  autoComplete="new-password"
                  value={passwordConfirm}
                  onChange={(event) => setPasswordConfirm(event.target.value)}
                  placeholder="비밀번호를 다시 입력"
                  disabled={busy}
                />
              </label>
            ) : null}
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <Button type="submit" disabled={busy || previewLoading}>
                {busy ? <LoaderCircle className="size-4 animate-spin" /> : null}
                {resetMode ? '비밀번호 저장' : inviteRequiresSignup ? '계정 만들기' : '비밀번호 로그인'}
              </Button>
              <Button type="button" variant="outline" onClick={() => router.push('/connectors')} disabled={busy}>
                연결 소스로 돌아가기
              </Button>
            </div>
          </form>

          <div className="mt-4 text-sm text-neutral-500">
            비밀번호를 잊었으면 워크스페이스 관리자에게 재설정 링크를 요청하세요.
          </div>
        </Card>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[70vh] w-full max-w-5xl items-center justify-center">
          <Card className="w-full max-w-xl p-6 text-sm text-neutral-500 dark:text-neutral-400">
            <div className="flex items-center gap-2">
              <LoaderCircle className="size-4 animate-spin" /> 로그인 화면을 준비하는 중입니다.
            </div>
          </Card>
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  )
}
