import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params
  const response = await proxyJson(`/v1/glossary/slug/${encodeURIComponent(slug)}`)
  return toNextJson(response)
}
