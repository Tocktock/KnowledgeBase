import {
  DocumentListResponse,
  DocumentRelationsResponse,
  DocumentViewResponse,
  JobSummary,
  SearchRequest,
  SearchResponse,
} from '@/lib/types'

const BACKEND_URL = process.env.KB_BACKEND_URL ?? 'http://localhost:8000'

async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Backend request failed: ${response.status} ${detail}`)
  }

  return (await response.json()) as T
}

export async function getRecentDocuments(limit = 12) {
  return backendFetch<DocumentListResponse>(`/v1/documents?limit=${limit}`)
}

export async function getDocumentBySlug(slug: string) {
  return backendFetch<DocumentViewResponse>(`/v1/documents/slug/${encodeURIComponent(slug)}`)
}

export async function getDocumentRelations(documentId: string, limit = 8) {
  return backendFetch<DocumentRelationsResponse>(`/v1/documents/${documentId}/relations?limit=${limit}`)
}

export async function getJobs() {
  return backendFetch<JobSummary[]>('/v1/jobs')
}

export async function semanticSearch(payload: SearchRequest) {
  return backendFetch<SearchResponse>('/v1/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
