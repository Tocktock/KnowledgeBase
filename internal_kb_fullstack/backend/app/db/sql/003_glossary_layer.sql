CREATE TABLE IF NOT EXISTS knowledge_concepts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  normalized_term text NOT NULL,
  public_slug text,
  display_term text NOT NULL,
  aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
  language_code varchar(12) NOT NULL DEFAULT 'ko',
  concept_type varchar(20) NOT NULL DEFAULT 'term'
    CHECK (concept_type IN ('term', 'product', 'process', 'team', 'metric', 'entity')),
  confidence_score double precision NOT NULL DEFAULT 0,
  support_doc_count integer NOT NULL DEFAULT 0,
  support_chunk_count integer NOT NULL DEFAULT 0,
  status varchar(20) NOT NULL DEFAULT 'suggested'
    CHECK (status IN ('suggested', 'drafted', 'approved', 'ignored', 'stale')),
  owner_team_hint text,
  source_system_mix jsonb NOT NULL DEFAULT '[]'::jsonb,
  generated_document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  canonical_document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  refreshed_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_status_confidence
  ON knowledge_concepts(status, confidence_score DESC, refreshed_at DESC);

CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_display_term_trgm
  ON knowledge_concepts USING gin (display_term gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_normalized_term_trgm
  ON knowledge_concepts USING gin (normalized_term gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_aliases_gin
  ON knowledge_concepts USING gin (aliases jsonb_path_ops);

DROP TRIGGER IF EXISTS trg_knowledge_concepts_touch_updated_at ON knowledge_concepts;
CREATE TRIGGER trg_knowledge_concepts_touch_updated_at
BEFORE UPDATE ON knowledge_concepts
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TABLE IF NOT EXISTS concept_supports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  concept_id uuid NOT NULL REFERENCES knowledge_concepts(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  revision_id uuid REFERENCES document_revisions(id) ON DELETE SET NULL,
  chunk_id uuid REFERENCES document_chunks(id) ON DELETE SET NULL,
  support_group_key text NOT NULL,
  evidence_kind varchar(20) NOT NULL
    CHECK (evidence_kind IN ('title', 'heading', 'table-field', 'alias', 'semantic', 'link-neighbor')),
  evidence_term text NOT NULL,
  support_text text NOT NULL,
  evidence_strength double precision NOT NULL DEFAULT 0,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_concept_support UNIQUE (concept_id, document_id, chunk_id, evidence_kind, evidence_term)
);

CREATE INDEX IF NOT EXISTS ix_concept_supports_concept_strength
  ON concept_supports(concept_id, evidence_strength DESC, evidence_kind);

CREATE INDEX IF NOT EXISTS ix_concept_supports_document_id
  ON concept_supports(document_id);

CREATE INDEX IF NOT EXISTS ix_concept_supports_group_key
  ON concept_supports(support_group_key);

CREATE TABLE IF NOT EXISTS glossary_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind varchar(20) NOT NULL CHECK (kind IN ('refresh', 'draft')),
  scope varchar(20) NOT NULL DEFAULT 'full' CHECK (scope IN ('full', 'incremental')),
  status varchar(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
  target_concept_id uuid REFERENCES knowledge_concepts(id) ON DELETE SET NULL,
  target_document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  priority integer NOT NULL DEFAULT 200,
  attempt_count integer NOT NULL DEFAULT 0,
  error_message text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  requested_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  last_heartbeat_at timestamptz,
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS ix_glossary_jobs_status_priority_requested
  ON glossary_jobs(status, priority, requested_at);

CREATE INDEX IF NOT EXISTS ix_glossary_jobs_kind_scope_status
  ON glossary_jobs(kind, scope, status);
