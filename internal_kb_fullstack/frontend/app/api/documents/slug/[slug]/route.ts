import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'
import { encodePathSegment } from '@/lib/path-segments'

export async function GET(request: NextRequest, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params
  const response = await proxyJson(`/v1/documents/slug/${encodePathSegment(slug)}`, {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
