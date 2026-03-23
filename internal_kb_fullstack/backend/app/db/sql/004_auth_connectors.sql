CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  google_subject text NOT NULL UNIQUE,
  email text NOT NULL UNIQUE,
  name text NOT NULL,
  avatar_url text,
  status varchar(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled')),
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_users_touch_updated_at ON users;
CREATE TRIGGER trg_users_touch_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TABLE IF NOT EXISTS user_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);

CREATE TABLE IF NOT EXISTS user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role varchar(20) NOT NULL CHECK (role IN ('admin', 'member')),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role)
);

CREATE TABLE IF NOT EXISTS connector_oauth_states (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  state text NOT NULL UNIQUE,
  purpose varchar(30) NOT NULL CHECK (purpose IN ('login', 'connect_drive')),
  owner_scope varchar(20) NOT NULL CHECK (owner_scope IN ('shared', 'user')),
  owner_user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  code_verifier text NOT NULL,
  return_path text NOT NULL DEFAULT '/',
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_connector_oauth_states_expires_at ON connector_oauth_states(expires_at);

CREATE TABLE IF NOT EXISTS connector_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider varchar(30) NOT NULL CHECK (provider IN ('google_drive')),
  owner_scope varchar(20) NOT NULL CHECK (owner_scope IN ('shared', 'user')),
  owner_user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  account_email text,
  account_subject text NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'needs_reauth', 'revoked', 'disconnected')),
  encrypted_access_token text NOT NULL,
  encrypted_refresh_token text,
  token_expires_at timestamptz,
  granted_scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
  last_validated_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_connector_connections_touch_updated_at ON connector_connections;
CREATE TRIGGER trg_connector_connections_touch_updated_at
BEFORE UPDATE ON connector_connections
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS ix_connector_connections_owner_scope
  ON connector_connections(owner_scope, owner_user_id);

CREATE TABLE IF NOT EXISTS connector_sync_targets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id uuid NOT NULL REFERENCES connector_connections(id) ON DELETE CASCADE,
  target_type varchar(20) NOT NULL CHECK (target_type IN ('folder', 'shared_drive')),
  external_id text NOT NULL,
  name text NOT NULL,
  include_subfolders boolean NOT NULL DEFAULT true,
  sync_mode varchar(20) NOT NULL DEFAULT 'manual' CHECK (sync_mode IN ('manual', 'auto')),
  sync_interval_minutes integer,
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
  sync_cursor text,
  last_sync_started_at timestamptz,
  last_sync_completed_at timestamptz,
  next_auto_sync_at timestamptz,
  last_sync_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_connector_target_external UNIQUE (connection_id, target_type, external_id)
);

DROP TRIGGER IF EXISTS trg_connector_sync_targets_touch_updated_at ON connector_sync_targets;
CREATE TRIGGER trg_connector_sync_targets_touch_updated_at
BEFORE UPDATE ON connector_sync_targets
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS ix_connector_sync_targets_connection_id
  ON connector_sync_targets(connection_id);

CREATE INDEX IF NOT EXISTS ix_connector_sync_targets_auto_due
  ON connector_sync_targets(sync_mode, next_auto_sync_at);

CREATE TABLE IF NOT EXISTS connector_source_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id uuid NOT NULL REFERENCES connector_connections(id) ON DELETE CASCADE,
  target_id uuid NOT NULL REFERENCES connector_sync_targets(id) ON DELETE CASCADE,
  external_file_id text NOT NULL,
  mime_type text,
  name text NOT NULL,
  source_url text,
  source_revision_id text,
  internal_document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  item_status varchar(20) NOT NULL CHECK (item_status IN ('imported', 'unchanged', 'unsupported', 'failed', 'deleted')),
  unsupported_reason text,
  error_message text,
  last_seen_at timestamptz,
  last_synced_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_connector_source_item_external UNIQUE (connection_id, target_id, external_file_id)
);

DROP TRIGGER IF EXISTS trg_connector_source_items_touch_updated_at ON connector_source_items;
CREATE TRIGGER trg_connector_source_items_touch_updated_at
BEFORE UPDATE ON connector_source_items
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS ix_connector_source_items_document_id
  ON connector_source_items(internal_document_id);

CREATE INDEX IF NOT EXISTS ix_connector_source_items_target_status
  ON connector_source_items(target_id, item_status);

CREATE TABLE IF NOT EXISTS connector_sync_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind varchar(30) NOT NULL DEFAULT 'connector_sync' CHECK (kind IN ('connector_sync')),
  connection_id uuid NOT NULL REFERENCES connector_connections(id) ON DELETE CASCADE,
  target_id uuid NOT NULL REFERENCES connector_sync_targets(id) ON DELETE CASCADE,
  sync_mode varchar(20) NOT NULL DEFAULT 'manual' CHECK (sync_mode IN ('manual', 'auto')),
  status varchar(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
  priority integer NOT NULL DEFAULT 90,
  attempt_count integer NOT NULL DEFAULT 0,
  error_message text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  requested_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  last_heartbeat_at timestamptz,
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS ix_connector_sync_jobs_status_priority_requested
  ON connector_sync_jobs(status, priority, requested_at);
