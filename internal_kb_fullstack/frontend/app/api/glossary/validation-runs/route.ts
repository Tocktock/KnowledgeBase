import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: NextRequest) {
  const response = await proxyJson(`/v1/glossary/validation-runs${request.nextUrl.search}`, {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}

export async function POST(request: NextRequest) {
  const response = await proxyJson('/v1/glossary/validation-runs', {
    method: 'POST',
    body: await request.text(),
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
