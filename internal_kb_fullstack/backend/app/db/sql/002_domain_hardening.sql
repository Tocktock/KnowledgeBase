DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_document_revisions_document_id_id'
  ) THEN
    ALTER TABLE document_revisions
      ADD CONSTRAINT uq_document_revisions_document_id_id UNIQUE (document_id, id);
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_documents_current_revision'
  ) THEN
    ALTER TABLE documents DROP CONSTRAINT fk_documents_current_revision;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_documents_current_revision_belongs_to_document'
  ) THEN
    ALTER TABLE documents
      ADD CONSTRAINT fk_documents_current_revision_belongs_to_document
      FOREIGN KEY (id, current_revision_id)
      REFERENCES document_revisions(document_id, id)
      DEFERRABLE INITIALLY DEFERRED;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_document_chunks_revision_belongs_to_document'
  ) THEN
    ALTER TABLE document_chunks
      ADD CONSTRAINT fk_document_chunks_revision_belongs_to_document
      FOREIGN KEY (document_id, revision_id)
      REFERENCES document_revisions(document_id, id)
      ON DELETE CASCADE;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_embedding_jobs_revision_belongs_to_document'
  ) THEN
    ALTER TABLE embedding_jobs
      ADD CONSTRAINT fk_embedding_jobs_revision_belongs_to_document
      FOREIGN KEY (document_id, revision_id)
      REFERENCES document_revisions(document_id, id)
      ON DELETE CASCADE;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_document_chunks_embedding_dimensions_fixed'
  ) THEN
    ALTER TABLE document_chunks
      ADD CONSTRAINT ck_document_chunks_embedding_dimensions_fixed
      CHECK (embedding_dimensions IS NULL OR embedding_dimensions = __EMBEDDING_DIMENSIONS__);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_embedding_cache_dimensions_fixed'
  ) THEN
    ALTER TABLE embedding_cache
      ADD CONSTRAINT ck_embedding_cache_dimensions_fixed
      CHECK (embedding_dimensions = __EMBEDDING_DIMENSIONS__);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_embedding_jobs_dimensions_fixed'
  ) THEN
    ALTER TABLE embedding_jobs
      ADD CONSTRAINT ck_embedding_jobs_dimensions_fixed
      CHECK (embedding_dimensions = __EMBEDDING_DIMENSIONS__);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS document_links (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  source_revision_id uuid NOT NULL REFERENCES document_revisions(id) ON DELETE CASCADE,
  target_slug text NOT NULL,
  target_document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  link_text text,
  link_anchor text,
  link_order integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_document_links_revision_order UNIQUE (source_revision_id, link_order),
  CONSTRAINT ck_document_links_target_slug_nonempty CHECK (length(target_slug) > 0)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_document_links_revision_belongs_to_document'
  ) THEN
    ALTER TABLE document_links
      ADD CONSTRAINT fk_document_links_revision_belongs_to_document
      FOREIGN KEY (source_document_id, source_revision_id)
      REFERENCES document_revisions(document_id, id)
      ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_document_links_source_document_id
  ON document_links(source_document_id);

CREATE INDEX IF NOT EXISTS ix_document_links_source_revision_id
  ON document_links(source_revision_id);

CREATE INDEX IF NOT EXISTS ix_document_links_target_slug
  ON document_links(target_slug);

CREATE INDEX IF NOT EXISTS ix_document_links_target_document_id
  ON document_links(target_document_id);
