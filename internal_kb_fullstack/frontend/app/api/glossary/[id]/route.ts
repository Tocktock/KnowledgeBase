import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(_request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const request = _request
  const { id } = await context.params
  const response = await proxyJson(`/v1/glossary/${id}`, {
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  const response = await proxyJson(`/v1/glossary/${id}`, {
    method: 'PATCH',
    body: await request.text(),
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}
