import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  const response = await proxyJson(`/v1/glossary/${id}`)
  return toNextJson(response)
}

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  const payload = await request.json()
  const response = await proxyJson(`/v1/glossary/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
  return toNextJson(response)
}
