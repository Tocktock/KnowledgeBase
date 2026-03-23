import { NextRequest, NextResponse } from 'next/server'

import type { AuthCallbackResponse } from '@/lib/types'
import { SESSION_COOKIE_NAME, proxyJson } from '@/lib/api/proxy'

function appUrl(request: NextRequest, path: string) {
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? 'localhost:3000'
  const protocol = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '') ?? 'http'
  return new URL(path, `${protocol}://${host}`)
}

export async function GET(request: NextRequest) {
  const search = request.nextUrl.search
  const response = await proxyJson(`/v1/auth/google/callback${search}`)
  if (!response.ok) {
    return NextResponse.redirect(appUrl(request, '/connectors?auth_error=login_failed'))
  }
  const payload = (await response.json()) as AuthCallbackResponse
  const redirectUrl = appUrl(request, payload.redirect_to || '/connectors')
  const nextResponse = NextResponse.redirect(redirectUrl)
  nextResponse.cookies.set(SESSION_COOKIE_NAME, payload.session_token, {
    path: '/',
    httpOnly: true,
    sameSite: 'lax',
    secure: request.nextUrl.protocol === 'https:',
    maxAge: 60 * 60 * 24 * 14,
  })
  return nextResponse
}
