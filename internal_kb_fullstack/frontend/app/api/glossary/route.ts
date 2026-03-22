import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(request: Request) {
  const { search } = new URL(request.url)
  const response = await proxyJson(`/v1/glossary${search}`)
  return toNextJson(response)
}

export async function POST(request: Request) {
  const payload = await request.json()
  const response = await proxyJson('/v1/glossary/refresh', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return toNextJson(response)
}
