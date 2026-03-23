import { NextRequest, NextResponse } from 'next/server'

import type { OAuthStartResponse } from '@/lib/types'
import { proxyJson } from '@/lib/api/proxy'

function appUrl(request: NextRequest, path: string) {
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? 'localhost:3000'
  const protocol = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '') ?? 'http'
  return new URL(path, `${protocol}://${host}`)
}

export async function GET(request: NextRequest) {
  const returnTo = request.nextUrl.searchParams.get('return_to') ?? '/connectors'
  const postAuthAction = request.nextUrl.searchParams.get('post_auth_action')
  const ownerScope = request.nextUrl.searchParams.get('owner_scope')
  const search = new URLSearchParams({ return_to: returnTo })
  if (postAuthAction) search.set('post_auth_action', postAuthAction)
  if (ownerScope) search.set('owner_scope', ownerScope)
  const response = await proxyJson(`/v1/auth/google/start?${search.toString()}`)
  if (!response.ok) {
    return NextResponse.redirect(appUrl(request, '/connectors?auth_error=login_unavailable'))
  }
  const payload = (await response.json()) as OAuthStartResponse
  return NextResponse.redirect(payload.authorization_url)
}
