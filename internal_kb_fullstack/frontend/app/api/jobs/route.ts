import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: NextRequest) {
  const response = await proxyJson('/v1/jobs', {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
