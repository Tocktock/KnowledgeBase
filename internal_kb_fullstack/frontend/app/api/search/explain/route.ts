import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: Request) {
  const payload = await request.json()
  const response = await proxyJson('/v1/search/explain', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return toNextJson(response)
}
