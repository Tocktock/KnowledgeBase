import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  const search = request.nextUrl.search
  const response = await proxyJson(`/v1/documents/${id}/relations${search}`, {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
