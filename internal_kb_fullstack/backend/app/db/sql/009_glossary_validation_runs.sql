CREATE TABLE IF NOT EXISTS glossary_validation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  requested_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  mode varchar(40) NOT NULL
    CHECK (mode IN ('sync_validate_impacted', 'sync_validate_full', 'validate_term')),
  status varchar(20) NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
  target_concept_id uuid REFERENCES knowledge_concepts(id) ON DELETE SET NULL,
  source_scope varchar(30) NOT NULL DEFAULT 'workspace_active',
  selected_resource_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_sync_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  linked_job_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  error_message text,
  requested_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_glossary_validation_runs_touch_updated_at ON glossary_validation_runs;
CREATE TRIGGER trg_glossary_validation_runs_touch_updated_at
BEFORE UPDATE ON glossary_validation_runs
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS ix_glossary_validation_runs_workspace_requested
  ON glossary_validation_runs(workspace_id, requested_at DESC);

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS visibility_scope varchar(20) NOT NULL DEFAULT 'member_visible';

ALTER TABLE documents
  DROP CONSTRAINT IF EXISTS documents_visibility_scope_check;

ALTER TABLE documents
  ADD CONSTRAINT documents_visibility_scope_check
  CHECK (visibility_scope IN ('member_visible', 'evidence_only'));

CREATE INDEX IF NOT EXISTS ix_documents_visibility_scope
  ON documents(visibility_scope);

ALTER TABLE connector_resources
  ADD COLUMN IF NOT EXISTS visibility_scope varchar(20) NOT NULL DEFAULT 'member_visible';

ALTER TABLE connector_resources
  ADD COLUMN IF NOT EXISTS selection_mode varchar(30) NOT NULL DEFAULT 'browse';

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS connector_resources_visibility_scope_check;

ALTER TABLE connector_resources
  ADD CONSTRAINT connector_resources_visibility_scope_check
  CHECK (visibility_scope IN ('member_visible', 'evidence_only'));

CREATE INDEX IF NOT EXISTS ix_connector_resources_visibility_scope
  ON connector_resources(visibility_scope);

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS connector_resources_resource_kind_check;

ALTER TABLE connector_resources
  ADD CONSTRAINT connector_resources_resource_kind_check
  CHECK (resource_kind IN ('folder', 'shared_drive', 'repository_docs', 'repository_evidence', 'page', 'database', 'export_upload'));

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS validation_state varchar(30) NOT NULL DEFAULT 'new_term';

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS validation_reason text;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS evidence_signature text;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS last_validation_run_id uuid REFERENCES glossary_validation_runs(id) ON DELETE SET NULL;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS last_validated_at timestamptz;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS review_required boolean NOT NULL DEFAULT false;

ALTER TABLE knowledge_concepts
  DROP CONSTRAINT IF EXISTS knowledge_concepts_validation_state_check;

ALTER TABLE knowledge_concepts
  ADD CONSTRAINT knowledge_concepts_validation_state_check
  CHECK (validation_state IN ('ok', 'needs_update', 'missing_draft', 'stale_evidence', 'new_term'));

CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_validation_state
  ON knowledge_concepts(validation_state, review_required);

UPDATE knowledge_concepts
SET
  validation_state = CASE
    WHEN status = 'approved' THEN 'ok'
    WHEN status = 'stale' THEN 'stale_evidence'
    WHEN status = 'ignored' THEN 'ok'
    ELSE 'new_term'
  END,
  validation_reason = CASE
    WHEN status = 'approved' THEN 'Approved glossary definition is awaiting validation drift checks.'
    WHEN status = 'stale' THEN 'Supporting evidence is no longer current.'
    WHEN status = 'ignored' THEN 'Concept is excluded from the active review queue.'
    ELSE 'Term requires glossary review before it becomes authoritative.'
  END,
  last_validated_at = COALESCE(last_validated_at, refreshed_at),
  review_required = CASE
    WHEN status IN ('approved', 'ignored') THEN false
    ELSE true
  END
WHERE last_validated_at IS NULL
   OR validation_reason IS NULL
   OR validation_state IS NULL;

ALTER TABLE glossary_jobs
  DROP CONSTRAINT IF EXISTS glossary_jobs_kind_check;

ALTER TABLE glossary_jobs
  ADD CONSTRAINT glossary_jobs_kind_check
  CHECK (kind IN ('refresh', 'draft', 'validation_run'));

ALTER TABLE glossary_jobs
  DROP CONSTRAINT IF EXISTS glossary_jobs_scope_check;

ALTER TABLE glossary_jobs
  ADD CONSTRAINT glossary_jobs_scope_check
  CHECK (scope IN ('full', 'incremental', 'term'));
