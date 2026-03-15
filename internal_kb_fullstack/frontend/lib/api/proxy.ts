const BACKEND_URL = process.env.KB_BACKEND_URL ?? 'http://api:8000'

export async function proxyJson(path: string, init?: RequestInit) {
  return fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  })
}

export async function toNextJson(response: Response) {
  const bodyText = await response.text()
  return new Response(bodyText, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
    },
  })
}
