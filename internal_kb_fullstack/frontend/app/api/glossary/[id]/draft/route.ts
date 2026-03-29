import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  const response = await proxyJson(`/v1/glossary/${id}/draft`, {
    method: 'POST',
    body: await request.text(),
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
