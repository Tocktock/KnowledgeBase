import { proxyJson, toNextJson } from '@/lib/api/proxy'

export async function GET() {
  const response = await proxyJson('/v1/jobs')
  return toNextJson(response)
}
