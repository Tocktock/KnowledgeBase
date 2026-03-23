import { NextRequest, NextResponse } from 'next/server'

import { SESSION_COOKIE_NAME, getSessionToken, proxyJson } from '@/lib/api/proxy'

export async function POST(request: NextRequest) {
  const response = await proxyJson('/v1/auth/logout', {
    method: 'POST',
    sessionToken: getSessionToken(request),
  })
  const bodyText = await response.text()
  const nextResponse = new NextResponse(bodyText, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
    },
  })
  nextResponse.cookies.set(SESSION_COOKIE_NAME, '', {
    path: '/',
    maxAge: 0,
    httpOnly: true,
    sameSite: 'lax',
  })
  return nextResponse
}
