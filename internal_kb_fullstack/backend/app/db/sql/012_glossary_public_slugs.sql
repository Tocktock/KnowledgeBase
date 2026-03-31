ALTER TABLE knowledge_concepts
  ADD COLUMN IF NOT EXISTS public_slug text;

CREATE OR REPLACE FUNCTION knowledgehub_concept_slugify(value text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT COALESCE(
    NULLIF(
      btrim(
        regexp_replace(
          translate(
            regexp_replace(lower(trim(COALESCE(value, ''))), '[[:cntrl:]]+', '', 'g'),
            E'!"#$%&''()*+,./:;<=>?@[\\]^`{|}~',
            ''
          ),
          '[-[:space:]]+',
          '-',
          'g'
        ),
        '-'
      ),
      ''
    ),
    substr(encode(digest(COALESCE(value, ''), 'sha256'), 'hex'), 1, 12)
  );
$$;

DO $$
DECLARE
  record_row record;
  base_slug text;
  candidate_slug text;
  id_prefix text;
BEGIN
  FOR record_row IN
    SELECT id, workspace_id, display_term, public_slug
    FROM knowledge_concepts
    ORDER BY workspace_id, created_at ASC, id ASC
  LOOP
    IF COALESCE(btrim(record_row.public_slug), '') <> '' THEN
      CONTINUE;
    END IF;

    base_slug := knowledgehub_concept_slugify(record_row.display_term);
    candidate_slug := base_slug;

    IF EXISTS (
      SELECT 1
      FROM knowledge_concepts
      WHERE workspace_id = record_row.workspace_id
        AND public_slug = candidate_slug
        AND id <> record_row.id
    ) THEN
      id_prefix := split_part(record_row.id::text, '-', 1);
      candidate_slug := base_slug || '-' || id_prefix;

      IF EXISTS (
        SELECT 1
        FROM knowledge_concepts
        WHERE workspace_id = record_row.workspace_id
          AND public_slug = candidate_slug
          AND id <> record_row.id
      ) THEN
        candidate_slug := base_slug || '-' || replace(record_row.id::text, '-', '');
      END IF;
    END IF;

    UPDATE knowledge_concepts
    SET public_slug = candidate_slug
    WHERE id = record_row.id;
  END LOOP;
END;
$$;

ALTER TABLE knowledge_concepts
  ALTER COLUMN public_slug SET NOT NULL;

DROP INDEX IF EXISTS uq_knowledge_concepts_workspace_public_slug;
CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_concepts_workspace_public_slug
  ON knowledge_concepts(workspace_id, public_slug);

DROP FUNCTION IF EXISTS knowledgehub_concept_slugify(text);
