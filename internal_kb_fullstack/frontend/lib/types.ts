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
  result_type?: string
  matched_concept_id?: string | null
  matched_concept_term?: string | null
  evidence_kind?: string | null
  evidence_strength?: number | null
  support_group_key?: string | null
  metadata: Record<string, unknown>
}

export type SearchResponse = {
  query: string
  resolved_concept_id?: string | null
  resolved_concept_term?: string | null
  weak_grounding?: boolean
  notes?: string[]
  hits: SearchHit[]
}

export type SearchExplainResponse = SearchResponse & {
  normalized_query: string
  resolved_concept_status?: string | null
  canonical_document_slug?: string | null
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
  kind: string
  title: string
  revision_id?: string | null
  target_concept_id?: string | null
  target_document_id?: string | null
  status: string
  embedding_model?: string | null
  embedding_dimensions?: number | null
  batch_size?: number | null
  priority: number
  attempt_count: number
  error_message?: string | null
  requested_at: string
  started_at?: string | null
  finished_at?: string | null
}

export type GlossaryConceptDocumentLink = {
  id: string
  slug: string
  title: string
  status: string
  doc_type: string
  owner_team?: string | null
}

export type GlossaryConceptSummary = {
  id: string
  slug: string
  normalized_term: string
  display_term: string
  aliases: string[]
  language_code: string
  concept_type: string
  confidence_score: number
  support_doc_count: number
  support_chunk_count: number
  status: string
  owner_team_hint?: string | null
  source_system_mix: string[]
  generated_document?: GlossaryConceptDocumentLink | null
  canonical_document?: GlossaryConceptDocumentLink | null
  metadata: Record<string, unknown>
  refreshed_at: string
  updated_at: string
}

export type GlossarySupportItem = {
  id: string
  document_id: string
  document_slug: string
  document_title: string
  document_status: string
  document_doc_type: string
  owner_team?: string | null
  revision_id?: string | null
  chunk_id?: string | null
  evidence_kind: string
  evidence_term: string
  evidence_strength: number
  support_group_key: string
  support_text: string
  metadata: Record<string, unknown>
}

export type GlossaryConceptDetailResponse = {
  concept: GlossaryConceptSummary
  supports: GlossarySupportItem[]
  related_concepts: GlossaryConceptSummary[]
}

export type GlossaryConceptListResponse = {
  items: GlossaryConceptSummary[]
  total: number
  limit: number
  offset: number
}

export type GlossaryRefreshRequest = {
  scope?: 'full' | 'incremental'
}

export type GlossaryDraftRequest = {
  domain?: string
  regenerate?: boolean
}

export type GlossaryConceptUpdateRequest = {
  action: 'approve' | 'ignore' | 'mark_stale' | 'suggest' | 'merge' | 'split'
  canonical_document_id?: string | null
  merge_into_concept_id?: string | null
  split_aliases?: string[]
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
  allow_slug_update?: boolean
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

export type SlugConflictDocument = {
  id: string
  slug: string
  title: string
  status: string
  owner_team?: string | null
}

export type SlugConflictDetail = {
  code: 'slug_conflict'
  message: string
  document: SlugConflictDocument
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
