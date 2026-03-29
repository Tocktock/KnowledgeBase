import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const response = await proxyJson(`/v1/glossary/validation-runs/${id}${request.nextUrl.search}`, {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
