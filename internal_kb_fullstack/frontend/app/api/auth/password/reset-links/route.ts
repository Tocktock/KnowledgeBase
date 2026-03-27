import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: NextRequest) {
  const bodyText = await request.text()
  const response = await proxyJson('/v1/auth/password/reset-links', {
    method: 'POST',
    body: bodyText || undefined,
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
