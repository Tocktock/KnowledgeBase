export type DocumentSummary = {
  id: string
  source_system: string
  source_external_id?: string | null
  source_url?: string | null
  slug: string
  title: string
  language_code: string
  doc_type: string
  status: string
  owner_team?: string | null
  metadata: Record<string, unknown>
  current_revision_id?: string | null
  created_at: string
  updated_at: string
  last_ingested_at?: string | null
}

export type RevisionSummary = {
  id: string
  document_id: string
  revision_number: number
  source_revision_id?: string | null
  checksum: string
  content_hash: string
  content_tokens: number
  word_count: number
  created_at: string
}

export type ChunkSummary = {
  id: string
  revision_id: string
  chunk_index: number
  heading_path: string[]
  section_title?: string | null
  content_tokens: number
  content_hash: string
  embedding_model?: string | null
  embedding_dimensions?: number | null
  embedding_generated_at?: string | null
}

export type HeadingSummary = {
  title: string
  id: string
}

export type DocumentListItem = DocumentSummary & {
  excerpt?: string | null
  revision_number?: number | null
  word_count?: number | null
  content_tokens?: number | null
}

export type DocumentListResponse = {
  items: DocumentListItem[]
  total: number
  limit: number
  offset: number
}

export type DocumentViewResponse = {
  document: DocumentSummary
  revision?: RevisionSummary | null
  content_markdown?: string | null
  content_text?: string | null
  headings: HeadingSummary[]
  linked_slugs: string[]
  chunks: ChunkSummary[]
}

export type DocumentRelationItem = {
  id: string
  slug: string
  title: string
  excerpt?: string | null
  owner_team?: string | null
  doc_type: string
  updated_at: string
}

export type DocumentRelationsResponse = {
  outgoing: DocumentRelationItem[]
  backlinks: DocumentRelationItem[]
  related: DocumentRelationItem[]
}

export type SearchHit = {
  chunk_id: string
  document_id: string
  revision_id: string
  document_title: string
  document_slug: string
  source_system: string
  source_url?: string | null
  section_title?: string | null
  heading_path: string[]
  content_text: string
  hybrid_score: number
  vector_score?: number | null
  keyword_score?: number | null
  metadata: Record<string, unknown>
}

export type SearchResponse = {
  query: string
  hits: SearchHit[]
}

export type SearchRequest = {
  query: string
  limit?: number
  doc_type?: string
  source_system?: string
  owner_team?: string
  include_debug_scores?: boolean
}

export type JobSummary = {
  id: string
  revision_id: string
  status: string
  embedding_model: string
  embedding_dimensions: number
  batch_size: number
  priority: number
  attempt_count: number
  error_message?: string | null
  requested_at: string
  started_at?: string | null
  finished_at?: string | null
}

export type IngestDocumentRequest = {
  source_system: string
  source_external_id?: string | null
  source_revision_id?: string | null
  source_url?: string | null
  slug?: string | null
  title: string
  content_type: 'markdown' | 'text' | 'html'
  content: string
  doc_type?: string
  language_code?: string
  owner_team?: string | null
  status?: 'draft' | 'published' | 'archived'
  metadata?: Record<string, unknown>
  priority?: number
}

export type IngestDocumentResponse = {
  document: DocumentSummary
  revision: RevisionSummary
  job?: JobSummary | null
  unchanged: boolean
}

export type DefinitionDraftReference = {
  index: number
  document_id: string
  document_title: string
  document_slug: string
  source_system: string
  source_url?: string | null
  section_title?: string | null
  heading_path: string[]
  excerpt: string
}

export type GenerateDefinitionDraftRequest = {
  topic: string
  domain?: string
  doc_type?: string
  source_system?: string
  owner_team?: string
  reference_limit?: number
  search_limit?: number
}

export type GenerateDefinitionDraftResponse = {
  title: string
  slug: string
  query: string
  markdown: string
  references: DefinitionDraftReference[]
}
