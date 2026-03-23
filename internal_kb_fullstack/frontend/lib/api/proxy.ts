import type { NextRequest } from 'next/server'

const BACKEND_URL = process.env.KB_BACKEND_URL ?? 'http://api:8000'
export const SESSION_COOKIE_NAME = 'kb_session'
export const SESSION_HEADER_NAME = 'X-KB-Session'

type ProxyInit = RequestInit & {
  sessionToken?: string | null
}

export function getSessionToken(request: NextRequest) {
  return request.cookies.get(SESSION_COOKIE_NAME)?.value ?? null
}

export async function proxyJson(path: string, init?: ProxyInit) {
  const { sessionToken, ...requestInit } = init ?? {}
  const headers = new Headers(init?.headers ?? {})
  if (!(init?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (sessionToken) {
    headers.set(SESSION_HEADER_NAME, sessionToken)
  }

  return fetch(`${BACKEND_URL}${path}`, {
    ...requestInit,
    headers,
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
