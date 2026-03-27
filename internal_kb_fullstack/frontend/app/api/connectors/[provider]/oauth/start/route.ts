import { NextRequest, NextResponse } from 'next/server'

import type { OAuthStartResponse } from '@/lib/types'
import { getSessionToken, proxyJson } from '@/lib/api/proxy'

function appUrl(request: NextRequest, path: string) {
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? 'localhost:3000'
  const protocol = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '') ?? 'http'
  return new URL(path, `${protocol}://${host}`)
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> },
) {
  const { provider } = await params
  const sessionToken = getSessionToken(request)
  const scope = request.nextUrl.searchParams.get('scope') ?? 'workspace'
  const returnTo = request.nextUrl.searchParams.get('return_to') ?? '/connectors'
  if (!sessionToken) {
    const search = new URLSearchParams({
      return_to: returnTo,
      post_auth_action: 'connect_provider',
      owner_scope: scope,
      provider,
    })
    return NextResponse.redirect(appUrl(request, `/login?${search.toString()}`))
  }
  const response = await proxyJson(
    `/v1/connectors/${encodeURIComponent(provider)}/oauth/start?owner_scope=${encodeURIComponent(scope)}&return_to=${encodeURIComponent(returnTo)}`,
    {
      method: 'POST',
      sessionToken,
    },
  )
  if (!response.ok) {
    const errorCode = response.status === 403 && scope === 'workspace' ? 'org_admin_required' : 'start_failed'
    return NextResponse.redirect(appUrl(request, `/connectors?connector_error=${errorCode}`))
  }
  const payload = (await response.json()) as OAuthStartResponse
  return NextResponse.redirect(payload.authorization_url)
}
