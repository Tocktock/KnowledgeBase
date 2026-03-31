import { NextRequest, NextResponse } from 'next/server'

import type { OAuthStartResponse } from '@/lib/types'
import { proxyJson } from '@/lib/api/proxy'
import { coerceInternalPath } from '@/lib/internal-paths'

function appUrl(request: NextRequest, path: string) {
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? 'localhost:3000'
  const protocol = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '') ?? 'http'
  return new URL(path, `${protocol}://${host}`)
}

export async function GET(request: NextRequest) {
  const returnTo = coerceInternalPath(request.nextUrl.searchParams.get('return_to'), '/connectors')
  const postAuthAction = request.nextUrl.searchParams.get('post_auth_action')
  const ownerScope = request.nextUrl.searchParams.get('owner_scope')
  const provider = request.nextUrl.searchParams.get('provider')
  const search = new URLSearchParams({ return_to: returnTo })
  if (postAuthAction) search.set('post_auth_action', postAuthAction)
  if (ownerScope) search.set('owner_scope', ownerScope)
  if (provider) search.set('provider', provider)
  const response = await proxyJson(`/v1/auth/google/start?${search.toString()}`)
  if (!response.ok) {
    const fallback = new URL('/login', request.nextUrl.origin)
    fallback.searchParams.set('auth_error', 'login_unavailable')
    fallback.searchParams.set('return_to', returnTo)
    if (postAuthAction) fallback.searchParams.set('post_auth_action', postAuthAction)
    if (ownerScope) fallback.searchParams.set('owner_scope', ownerScope)
    if (provider) fallback.searchParams.set('provider', provider)
    return NextResponse.redirect(fallback)
  }
  const payload = (await response.json()) as OAuthStartResponse
  return NextResponse.redirect(payload.authorization_url)
}
