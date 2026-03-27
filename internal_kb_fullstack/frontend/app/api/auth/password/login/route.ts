import { NextRequest, NextResponse } from 'next/server'

import type { AuthSessionResponse } from '@/lib/types'
import { SESSION_COOKIE_NAME, proxyJson } from '@/lib/api/proxy'

export async function POST(request: NextRequest) {
  const bodyText = await request.text()
  const response = await proxyJson('/v1/auth/password/login', {
    method: 'POST',
    body: bodyText || undefined,
  })
  const payloadText = await response.text()
  const nextResponse = new NextResponse(payloadText, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
    },
  })
  if (response.ok) {
    const payload = JSON.parse(payloadText) as AuthSessionResponse
    nextResponse.cookies.set(SESSION_COOKIE_NAME, payload.session_token, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: request.nextUrl.protocol === 'https:',
      maxAge: 60 * 60 * 24 * 14,
    })
  }
  return nextResponse
}
