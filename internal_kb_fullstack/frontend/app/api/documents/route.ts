import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: NextRequest) {
  const search = request.nextUrl.search
  const response = await proxyJson(`/v1/documents${search}`, {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}

export async function POST(request: NextRequest) {
  const payload = await request.json()
  const response = await proxyJson('/v1/documents/ingest', {
    method: 'POST',
    body: JSON.stringify(payload),
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
