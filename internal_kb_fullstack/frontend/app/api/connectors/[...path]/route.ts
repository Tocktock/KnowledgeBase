import { NextRequest } from 'next/server'

import { getSessionToken, proxyJson, toNextJson } from '@/lib/api/proxy'

async function forward(request: NextRequest, path: string[]) {
  const search = request.nextUrl.search
  const contentType = request.headers.get('content-type') ?? ''
  const body =
    request.method === 'POST' || request.method === 'PATCH'
      ? contentType.includes('multipart/form-data')
        ? await request.formData()
        : await request.text()
      : undefined
  const response = await proxyJson(`/v1/connectors/${path.join('/')}${search}`, {
    method: request.method,
    body: body instanceof FormData ? body : body || undefined,
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
