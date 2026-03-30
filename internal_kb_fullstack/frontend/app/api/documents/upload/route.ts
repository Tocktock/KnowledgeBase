import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: NextRequest) {
  const formData = await request.formData()
  const response = await proxyJson('/v1/documents/upload', {
    method: 'POST',
    body: formData,
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
