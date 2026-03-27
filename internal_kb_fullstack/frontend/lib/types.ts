export type TrustSummary = {
  source_label: string
  source_url?: string | null
  authority_kind: string
  last_synced_at?: string | null
  freshness_state: string
  evidence_count: number
}

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
  trust: TrustSummary
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
  trust: TrustSummary
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
  resource_id?: string | null
  connection_id?: string | null
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
  trust: TrustSummary
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
  trust: TrustSummary
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

export type UserSummary = {
  id: string
  email: string
  name: string
  avatar_url?: string | null
  roles: string[]
  is_admin: boolean
  last_login_at?: string | null
  current_workspace?: WorkspaceSummary | null
  current_workspace_role?: string | null
  can_manage_workspace_connectors: boolean
}

export type AuthMeResponse = {
  authenticated: boolean
  user?: UserSummary | null
}

export type OAuthStartResponse = {
  authorization_url: string
  state: string
}

export type AuthSessionResponse = {
  session_token: string
  redirect_to: string
  user: UserSummary
}

export type AuthCallbackResponse = AuthSessionResponse

export type PasswordLoginRequest = {
  email: string
  password: string
  return_to?: string
  post_auth_action?: string | null
  owner_scope?: string | null
  provider?: string | null
  invite_token?: string | null
}

export type PasswordInviteSignupRequest = {
  invite_token: string
  name: string
  password: string
  return_to?: string
  post_auth_action?: string | null
  owner_scope?: string | null
  provider?: string | null
}

export type PasswordResetLinkCreateRequest = {
  email: string
}

export type PasswordResetLinkCreateResponse = {
  email: string
  reset_url: string
  expires_at: string
}

export type PasswordResetPreviewResponse = {
  email: string
  name: string
  expires_at: string
  used_at?: string | null
  is_expired: boolean
}

export type PasswordResetConsumeRequest = {
  password: string
  return_to?: string
  post_auth_action?: string | null
  owner_scope?: string | null
  provider?: string | null
}

export type WorkspaceSummary = {
  id: string
  slug: string
  name: string
  is_default: boolean
}

export type WorkspaceContextResponse = {
  workspace?: WorkspaceSummary | null
  role?: string | null
  can_manage_connectors: boolean
}

export type WorkspaceSourceHealthSummary = {
  workspace_connection_count: number
  healthy_source_count: number
  needs_attention_count: number
  providers_needing_attention: string[]
}

export type WorkspaceOverviewResponse = {
  authenticated: boolean
  workspace?: WorkspaceSummary | null
  viewer_role?: string | null
  can_manage_connectors: boolean
  setup_state: string
  next_actions: string[]
  source_health: WorkspaceSourceHealthSummary
  featured_docs: DocumentListItem[]
  featured_concepts: GlossaryConceptSummary[]
  recent_sync_issues: JobSummary[]
}

export type WorkspaceMemberSummary = {
  user_id: string
  email: string
  name: string
  avatar_url?: string | null
  role: string
  created_at: string
}

export type WorkspaceInvitationSummary = {
  id: string
  workspace_id: string
  invited_email: string
  role: string
  expires_at: string
  accepted_at?: string | null
  created_at: string
}

export type WorkspaceInvitationCreateRequest = {
  invited_email: string
  role: string
}

export type WorkspaceInvitationCreateResponse = {
  invitation: WorkspaceInvitationSummary
  invite_url: string
}

export type WorkspaceInvitationAcceptResponse = {
  workspace: WorkspaceSummary
  role: string
}

export type WorkspaceInvitationPreviewResponse = {
  invited_email: string
  workspace: WorkspaceSummary
  role: string
  expires_at: string
  accepted_at?: string | null
  is_expired: boolean
  local_password_exists: boolean
}

export type ConnectorResourceSummary = {
  id: string
  connection_id: string
  provider: string
  resource_kind: string
  external_id: string
  name: string
  resource_url?: string | null
  parent_external_id?: string | null
  sync_children: boolean
  sync_mode: string
  sync_interval_minutes?: number | null
  status: string
  last_sync_started_at?: string | null
  last_sync_completed_at?: string | null
  next_auto_sync_at?: string | null
  last_sync_summary: Record<string, number>
  provider_metadata: Record<string, unknown>
}

export type ConnectorConnectionSummary = {
  id: string
  provider: string
  owner_scope: string
  owner_user_id?: string | null
  display_name: string
  account_email?: string | null
  account_subject: string
  status: string
  granted_scopes: string[]
  last_validated_at?: string | null
  created_at: string
  updated_at: string
  resources: ConnectorResourceSummary[]
}

export type ConnectorListResponse = {
  items: ConnectorConnectionSummary[]
}

export type ConnectorReadinessResponse = {
  providers: ConnectorProviderReadiness[]
}

export type ConnectorProviderReadiness = {
  provider: string
  oauth_configured: boolean
  workspace_connection_exists: boolean
  workspace_connection_status?: string | null
  viewer_can_manage_workspace_connection: boolean
  setup_state: string
  healthy_source_count: number
  needs_attention_count: number
  recommended_templates: string[]
}

export type ConnectorBrowseItem = {
  id: string
  name: string
  resource_kind: string
  resource_url?: string | null
  parent_external_id?: string | null
  has_children: boolean
  provider_metadata: Record<string, unknown>
}

export type ConnectorBrowseResponse = {
  items: ConnectorBrowseItem[]
  kind?: string | null
  parent_external_id?: string | null
  cursor?: string | null
  has_more: boolean
}

export type ConnectorSourceItemSummary = {
  id: string
  resource_id: string
  external_item_id: string
  mime_type?: string | null
  name: string
  source_url?: string | null
  source_revision_id?: string | null
  internal_document_id?: string | null
  item_status: string
  unsupported_reason?: string | null
  error_message?: string | null
  last_seen_at?: string | null
  last_synced_at?: string | null
  provider_metadata: Record<string, unknown>
}

export type ConnectorResourceCreateRequest = {
  resource_kind: string
  external_id: string
  name: string
  resource_url?: string | null
  parent_external_id?: string | null
  sync_children?: boolean | null
  sync_mode?: string | null
  sync_interval_minutes?: number | null
  provider_metadata?: Record<string, unknown>
}

export type ConnectorResourceUpdateRequest = {
  sync_children?: boolean | null
  sync_mode?: string | null
  sync_interval_minutes?: number | null
  status?: string | null
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
