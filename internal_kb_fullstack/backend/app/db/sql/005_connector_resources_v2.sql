UPDATE connector_oauth_states
SET purpose = 'connect_provider'
WHERE purpose = 'connect_drive';

ALTER TABLE connector_oauth_states
  DROP CONSTRAINT IF EXISTS connector_oauth_states_purpose_check;

ALTER TABLE connector_oauth_states
  ADD CONSTRAINT connector_oauth_states_purpose_check
  CHECK (purpose IN ('login', 'connect_provider'));

ALTER TABLE connector_connections
  DROP CONSTRAINT IF EXISTS connector_connections_provider_check;

ALTER TABLE connector_connections
  ADD CONSTRAINT connector_connections_provider_check
  CHECK (provider IN ('google_drive', 'notion'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_connector_connections_shared_provider
  ON connector_connections(provider, owner_scope)
  WHERE owner_user_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_connector_connections_user_provider
  ON connector_connections(provider, owner_scope, owner_user_id)
  WHERE owner_user_id IS NOT NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'connector_sync_targets'
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'connector_resources'
  ) THEN
    ALTER TABLE connector_sync_targets RENAME TO connector_resources;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'connector_resources' AND column_name = 'target_type'
  ) THEN
    ALTER TABLE connector_resources RENAME COLUMN target_type TO resource_kind;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'connector_resources' AND column_name = 'include_subfolders'
  ) THEN
    ALTER TABLE connector_resources RENAME COLUMN include_subfolders TO sync_children;
  END IF;
END $$;

ALTER TABLE connector_resources
  ADD COLUMN IF NOT EXISTS provider varchar(30);

UPDATE connector_resources resources
SET provider = connections.provider
FROM connector_connections connections
WHERE resources.connection_id = connections.id
  AND (resources.provider IS NULL OR resources.provider = '');

ALTER TABLE connector_resources
  ALTER COLUMN provider SET NOT NULL;

ALTER TABLE connector_resources
  ADD COLUMN IF NOT EXISTS resource_url text;

ALTER TABLE connector_resources
  ADD COLUMN IF NOT EXISTS parent_external_id text;

ALTER TABLE connector_resources
  ADD COLUMN IF NOT EXISTS provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS connector_sync_targets_target_type_check;

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS connector_resources_resource_kind_check;

ALTER TABLE connector_resources
  ADD CONSTRAINT connector_resources_resource_kind_check
  CHECK (resource_kind IN ('folder', 'shared_drive', 'page', 'database'));

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS uq_connector_target_external;

ALTER TABLE connector_resources
  DROP CONSTRAINT IF EXISTS uq_connector_resource_external;

ALTER TABLE connector_resources
  ADD CONSTRAINT uq_connector_resource_external UNIQUE (connection_id, resource_kind, external_id);

DROP TRIGGER IF EXISTS trg_connector_sync_targets_touch_updated_at ON connector_resources;
DROP TRIGGER IF EXISTS trg_connector_resources_touch_updated_at ON connector_resources;
CREATE TRIGGER trg_connector_resources_touch_updated_at
BEFORE UPDATE ON connector_resources
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP INDEX IF EXISTS ix_connector_sync_targets_connection_id;
DROP INDEX IF EXISTS ix_connector_sync_targets_auto_due;
CREATE INDEX IF NOT EXISTS ix_connector_resources_connection_id
  ON connector_resources(connection_id);
CREATE INDEX IF NOT EXISTS ix_connector_resources_auto_due
  ON connector_resources(sync_mode, next_auto_sync_at);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'connector_source_items' AND column_name = 'target_id'
  ) THEN
    ALTER TABLE connector_source_items RENAME COLUMN target_id TO resource_id;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'connector_source_items' AND column_name = 'external_file_id'
  ) THEN
    ALTER TABLE connector_source_items RENAME COLUMN external_file_id TO external_item_id;
  END IF;
END $$;

ALTER TABLE connector_source_items
  ADD COLUMN IF NOT EXISTS provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE connector_source_items
  DROP CONSTRAINT IF EXISTS uq_connector_source_item_external;

ALTER TABLE connector_source_items
  ADD CONSTRAINT uq_connector_source_item_external UNIQUE (connection_id, resource_id, external_item_id);

DROP TRIGGER IF EXISTS trg_connector_source_items_touch_updated_at ON connector_source_items;
CREATE TRIGGER trg_connector_source_items_touch_updated_at
BEFORE UPDATE ON connector_source_items
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP INDEX IF EXISTS ix_connector_source_items_target_status;
CREATE INDEX IF NOT EXISTS ix_connector_source_items_resource_status
  ON connector_source_items(resource_id, item_status);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'connector_sync_jobs' AND column_name = 'target_id'
  ) THEN
    ALTER TABLE connector_sync_jobs RENAME COLUMN target_id TO resource_id;
  END IF;
END $$;
