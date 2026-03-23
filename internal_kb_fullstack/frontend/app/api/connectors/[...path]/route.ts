import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

async function forward(request: NextRequest, path: string[]) {
  const search = request.nextUrl.search
  const bodyText =
    request.method === 'POST' || request.method === 'PATCH'
      ? await request.text()
      : ''
  const response = await proxyJson(`/v1/connectors/${path.join('/')}${search}`, {
    method: request.method,
    body: bodyText || undefined,
    sessionToken: getSessionToken(request),
  })
  return toNextJson(response)
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}
