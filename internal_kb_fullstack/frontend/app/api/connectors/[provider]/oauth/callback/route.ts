import { NextRequest, NextResponse } from 'next/server'

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
  if (!sessionToken) {
    return NextResponse.redirect(appUrl(request, '/connectors?connector_error=session_missing'))
  }
  const response = await proxyJson(`/v1/connectors/${encodeURIComponent(provider)}/oauth/callback${request.nextUrl.search}`, {
    sessionToken,
  })
  if (!response.ok) {
    return NextResponse.redirect(appUrl(request, '/connectors?connector_error=callback_failed'))
  }
  const payload = (await response.json()) as { redirect_to: string }
  return NextResponse.redirect(appUrl(request, payload.redirect_to || '/connectors'))
}
