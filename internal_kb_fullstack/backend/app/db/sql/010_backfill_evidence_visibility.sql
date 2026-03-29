UPDATE documents
SET visibility_scope = 'evidence_only'
WHERE source_system = 'notion-export'
   OR COALESCE(metadata->>'corpus_role', '') = 'glossary_evidence';

UPDATE connector_resources
SET visibility_scope = 'evidence_only'
WHERE resource_kind IN ('repository_evidence', 'export_upload')
   OR selection_mode = 'export_upload';
