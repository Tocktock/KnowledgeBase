import {
  DocumentListResponse,
  DocumentRelationsResponse,
  DocumentViewResponse,
  GlossaryConceptDetailResponse,
  GlossaryConceptListResponse,
  JobSummary,
  SearchRequest,
  SearchExplainResponse,
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

export async function explainSearch(payload: SearchRequest) {
  return backendFetch<SearchExplainResponse>('/v1/search/explain', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getGlossaryConcepts(params?: {
  query?: string
  status?: string
  concept_type?: string
  owner_team?: string
  limit?: number
  offset?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.query) searchParams.set('query', params.query)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.concept_type) searchParams.set('concept_type', params.concept_type)
  if (params?.owner_team) searchParams.set('owner_team', params.owner_team)
  if (typeof params?.limit === 'number') searchParams.set('limit', String(params.limit))
  if (typeof params?.offset === 'number') searchParams.set('offset', String(params.offset))
  const suffix = searchParams.toString() ? `?${searchParams}` : ''
  return backendFetch<GlossaryConceptListResponse>(`/v1/glossary${suffix}`)
}

export async function getGlossaryConceptBySlug(slug: string) {
  return backendFetch<GlossaryConceptDetailResponse>(`/v1/glossary/slug/${encodeURIComponent(slug)}`)
}
