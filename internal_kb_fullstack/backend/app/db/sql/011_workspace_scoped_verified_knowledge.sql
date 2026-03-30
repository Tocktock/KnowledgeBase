CREATE TABLE IF NOT EXISTS glossary_verification_policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  label text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  min_support_docs integer NOT NULL DEFAULT 2,
  freshness_sla_days integer NOT NULL DEFAULT 30,
  min_durable_sources integer NOT NULL DEFAULT 1,
  allow_evidence_only_support boolean NOT NULL DEFAULT true,
  continuous_revalidation_enabled boolean NOT NULL DEFAULT true,
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_glossary_verification_policy_workspace_label_version
    UNIQUE (workspace_id, label, version)
);

DROP TRIGGER IF EXISTS trg_glossary_verification_policies_touch_updated_at ON glossary_verification_policies;
CREATE TRIGGER trg_glossary_verification_policies_touch_updated_at
BEFORE UPDATE ON glossary_verification_policies
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE UNIQUE INDEX IF NOT EXISTS uq_glossary_verification_policies_workspace_default
  ON glossary_verification_policies(workspace_id)
  WHERE is_default = true;

INSERT INTO glossary_verification_policies (
  workspace_id,
  label,
  version,
  min_support_docs,
  freshness_sla_days,
  min_durable_sources,
  allow_evidence_only_support,
  continuous_revalidation_enabled,
  is_default
)
SELECT
  workspaces.id,
  'Default glossary verification',
  1,
  2,
  30,
  1,
  true,
  true,
  true
FROM workspaces
WHERE NOT EXISTS (
  SELECT 1
  FROM glossary_verification_policies
  WHERE glossary_verification_policies.workspace_id = workspaces.id
    AND glossary_verification_policies.is_default = true
);

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE;

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
UPDATE documents
SET workspace_id = default_workspace.id
FROM default_workspace
WHERE documents.workspace_id IS NULL;

ALTER TABLE documents
  ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE documents
  DROP CONSTRAINT IF EXISTS uq_documents_source_external;

ALTER TABLE documents
  DROP CONSTRAINT IF EXISTS documents_slug_key;

ALTER TABLE documents
  DROP CONSTRAINT IF EXISTS uq_documents_workspace_slug;

ALTER TABLE documents
  ADD CONSTRAINT uq_documents_workspace_slug UNIQUE (workspace_id, slug);

DROP INDEX IF EXISTS uq_documents_workspace_source_external;
CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_workspace_source_external
  ON documents(workspace_id, source_system, source_external_id)
  WHERE source_external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_documents_workspace_visibility
  ON documents(workspace_id, visibility_scope);

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verification_policy_id uuid REFERENCES glossary_verification_policies(id) ON DELETE SET NULL;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verification_state varchar(30) NOT NULL DEFAULT 'evidence_insufficient';

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verification_reason text;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verified_at timestamptz;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verification_due_at timestamptz;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS last_checked_at timestamptz;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verified_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS verification_policy_version integer;

ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS evidence_bundle_hash text;

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
UPDATE knowledge_concepts
SET workspace_id = default_workspace.id
FROM default_workspace
WHERE knowledge_concepts.workspace_id IS NULL;

ALTER TABLE knowledge_concepts
  ALTER COLUMN workspace_id SET NOT NULL;

WITH default_policies AS (
  SELECT DISTINCT ON (workspace_id)
    workspace_id,
    id,
    version,
    freshness_sla_days,
    min_support_docs
  FROM glossary_verification_policies
  WHERE is_default = true
  ORDER BY workspace_id, version DESC, created_at DESC
)
UPDATE knowledge_concepts
SET
  verification_policy_id = default_policies.id,
  verification_policy_version = COALESCE(knowledge_concepts.verification_policy_version, default_policies.version),
  evidence_bundle_hash = COALESCE(knowledge_concepts.evidence_bundle_hash, knowledge_concepts.evidence_signature),
  last_checked_at = COALESCE(knowledge_concepts.last_checked_at, knowledge_concepts.last_validated_at, now()),
  verification_due_at = COALESCE(
    knowledge_concepts.verification_due_at,
    COALESCE(knowledge_concepts.last_validated_at, now()) + make_interval(days => default_policies.freshness_sla_days)
  ),
  verified_at = COALESCE(
    knowledge_concepts.verified_at,
    CASE
      WHEN knowledge_concepts.status = 'approved' THEN COALESCE(knowledge_concepts.last_validated_at, now())
      ELSE NULL
    END
  ),
  verification_state = CASE
    WHEN knowledge_concepts.status = 'archived' THEN 'archived'
    WHEN knowledge_concepts.status = 'approved' THEN 'verified'
    WHEN knowledge_concepts.support_doc_count >= default_policies.min_support_docs THEN 'monitoring'
    ELSE 'evidence_insufficient'
  END,
  verification_reason = COALESCE(
    knowledge_concepts.verification_reason,
    CASE
      WHEN knowledge_concepts.status = 'archived' THEN knowledge_concepts.display_term || ' is archived and no longer participates in continuous verification.'
      WHEN knowledge_concepts.status = 'approved' THEN knowledge_concepts.display_term || ' satisfies the workspace verification policy.'
      WHEN knowledge_concepts.support_doc_count >= default_policies.min_support_docs THEN knowledge_concepts.display_term || ' has enough evidence to keep monitoring before approval.'
      ELSE knowledge_concepts.display_term || ' does not yet satisfy the workspace verification policy.'
    END
  )
FROM default_policies
WHERE knowledge_concepts.workspace_id = default_policies.workspace_id
  AND knowledge_concepts.verification_policy_id IS NULL;

ALTER TABLE knowledge_concepts
  DROP CONSTRAINT IF EXISTS knowledge_concepts_normalized_term_key;

DROP INDEX IF EXISTS uq_knowledge_concepts_workspace_normalized_term;
CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_concepts_workspace_normalized_term
  ON knowledge_concepts(workspace_id, normalized_term);

ALTER TABLE knowledge_concepts
  DROP CONSTRAINT IF EXISTS knowledge_concepts_status_check;

ALTER TABLE knowledge_concepts
  ADD CONSTRAINT knowledge_concepts_status_check
  CHECK (status IN ('suggested', 'drafted', 'approved', 'ignored', 'stale', 'archived'));

ALTER TABLE knowledge_concepts
  DROP CONSTRAINT IF EXISTS knowledge_concepts_verification_state_check;

ALTER TABLE knowledge_concepts
  ADD CONSTRAINT knowledge_concepts_verification_state_check
  CHECK (verification_state IN ('verified', 'monitoring', 'drift_detected', 'evidence_insufficient', 'archived'));

DROP INDEX IF EXISTS ix_knowledge_concepts_validation_state;
CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_workspace_validation_state
  ON knowledge_concepts(workspace_id, validation_state, review_required);

CREATE INDEX IF NOT EXISTS ix_knowledge_concepts_verification_state
  ON knowledge_concepts(workspace_id, verification_state);

ALTER TABLE glossary_jobs
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE;

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
UPDATE glossary_jobs
SET workspace_id = COALESCE(
  glossary_jobs.workspace_id,
  (
    SELECT knowledge_concepts.workspace_id
    FROM knowledge_concepts
    WHERE knowledge_concepts.id = glossary_jobs.target_concept_id
  ),
  (
    SELECT documents.workspace_id
    FROM documents
    WHERE documents.id = glossary_jobs.target_document_id
  ),
  default_workspace.id
)
FROM default_workspace
WHERE glossary_jobs.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_glossary_jobs_workspace_status_requested
  ON glossary_jobs(workspace_id, status, requested_at);
