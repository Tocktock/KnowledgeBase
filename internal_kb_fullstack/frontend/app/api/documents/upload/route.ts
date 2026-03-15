import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: Request) {
  const formData = await request.formData()
  const response = await proxyJson('/v1/documents/upload', {
    method: 'POST',
    body: formData,
  })
  return toNextJson(response)
}
