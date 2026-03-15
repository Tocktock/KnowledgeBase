import { NextRequest } from 'next/server'

import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: NextRequest) {
  const search = request.nextUrl.search
  const response = await proxyJson(`/v1/documents${search}`)
  return toNextJson(response)
}

export async function POST(request: NextRequest) {
  const payload = await request.json()
  const response = await proxyJson('/v1/documents/ingest', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return toNextJson(response)
}
