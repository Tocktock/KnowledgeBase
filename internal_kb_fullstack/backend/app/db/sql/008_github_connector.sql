ALTER TABLE connector_connections
  DROP CONSTRAINT IF EXISTS connector_connections_provider_check;

ALTER TABLE connector_connections
  ADD CONSTRAINT connector_connections_provider_check
  CHECK (provider IN ('google_drive', 'github', 'notion'));

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS connector_resources_resource_kind_check;

ALTER TABLE connector_resources
  ADD CONSTRAINT connector_resources_resource_kind_check
  CHECK (resource_kind IN ('folder', 'shared_drive', 'repository_docs', 'page', 'database'));
