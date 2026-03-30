import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: NextRequest) {
  const payload = await request.json()
  const response = await proxyJson('/v1/search/explain', {
    method: 'POST',
    body: JSON.stringify(payload),
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
