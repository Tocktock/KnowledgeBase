import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  const payload = await request.json()
  const response = await proxyJson(`/v1/glossary/${id}/draft`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return toNextJson(response)
}
