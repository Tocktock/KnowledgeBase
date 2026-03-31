CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_system text NOT NULL,
  source_external_id text,
  source_url text,
  slug text NOT NULL,
  title text NOT NULL,
  language_code varchar(12) NOT NULL DEFAULT 'ko',
  doc_type varchar(50) NOT NULL DEFAULT 'knowledge',
  status varchar(20) NOT NULL DEFAULT 'published' CHECK (status IN ('draft', 'published', 'archived')),
  owner_team text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  current_revision_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  last_ingested_at timestamptz
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_external_partial
  ON documents(source_system, source_external_id)
  WHERE source_external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_documents_metadata_gin
  ON documents USING gin (metadata jsonb_path_ops);

CREATE INDEX IF NOT EXISTS ix_documents_title_trgm
  ON documents USING gin (title gin_trgm_ops);

CREATE TABLE IF NOT EXISTS document_revisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  revision_number integer NOT NULL,
  source_revision_id text,
  checksum text NOT NULL,
  content_hash text NOT NULL,
  content_markdown text,
  content_text text NOT NULL,
  content_tokens integer NOT NULL DEFAULT 0,
  word_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_document_revision_number UNIQUE(document_id, revision_number)
);

CREATE INDEX IF NOT EXISTS ix_document_revisions_document_created
  ON document_revisions(document_id, created_at DESC);

ALTER TABLE documents
  ADD CONSTRAINT fk_documents_current_revision
  FOREIGN KEY (current_revision_id) REFERENCES document_revisions(id)
  DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE IF NOT EXISTS document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  revision_id uuid NOT NULL REFERENCES document_revisions(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  heading_path text[] NOT NULL DEFAULT '{}'::text[],
  section_title text,
  content_text text NOT NULL,
  content_tokens integer NOT NULL DEFAULT 0,
  content_hash text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(section_title, '') || ' ' || content_text)) STORED,
  embedding vector(__EMBEDDING_DIMENSIONS__),
  embedding_model varchar(100),
  embedding_dimensions integer,
  embedding_generated_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_document_chunk_revision_index UNIQUE(revision_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_revision_id ON document_chunks(revision_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_content_hash ON document_chunks(content_hash);
CREATE INDEX IF NOT EXISTS ix_document_chunks_search_vector ON document_chunks USING gin(search_vector);
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
  ON document_chunks USING hnsw (embedding vector_cosine_ops)
  WHERE embedding IS NOT NULL;

CREATE TABLE IF NOT EXISTS embedding_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hash text NOT NULL,
  embedding_model varchar(100) NOT NULL,
  embedding_dimensions integer NOT NULL,
  token_count integer NOT NULL DEFAULT 0,
  embedding vector(__EMBEDDING_DIMENSIONS__) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_embedding_cache_lookup UNIQUE(content_hash, embedding_model, embedding_dimensions)
);

CREATE INDEX IF NOT EXISTS ix_embedding_cache_lookup
  ON embedding_cache(content_hash, embedding_model, embedding_dimensions);

CREATE TABLE IF NOT EXISTS embedding_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  revision_id uuid NOT NULL REFERENCES document_revisions(id) ON DELETE CASCADE,
  status varchar(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
  embedding_model varchar(100) NOT NULL,
  embedding_dimensions integer NOT NULL,
  batch_size integer NOT NULL DEFAULT 32,
  priority integer NOT NULL DEFAULT 100,
  attempt_count integer NOT NULL DEFAULT 0,
  error_message text,
  requested_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  last_heartbeat_at timestamptz,
  finished_at timestamptz,
  CONSTRAINT uq_embedding_job_revision_model UNIQUE(revision_id, embedding_model, embedding_dimensions)
);

CREATE INDEX IF NOT EXISTS ix_embedding_jobs_status_priority_requested
  ON embedding_jobs(status, priority, requested_at);

DROP TRIGGER IF EXISTS trg_documents_touch_updated_at ON documents;
CREATE TRIGGER trg_documents_touch_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_document_chunks_touch_updated_at ON document_chunks;
CREATE TRIGGER trg_document_chunks_touch_updated_at
BEFORE UPDATE ON document_chunks
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
