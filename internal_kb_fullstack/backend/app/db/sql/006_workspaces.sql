CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_workspaces_touch_updated_at ON workspaces;
CREATE TRIGGER trg_workspaces_touch_updated_at
BEFORE UPDATE ON workspaces
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_single_default
  ON workspaces(is_default)
  WHERE is_default = true;

CREATE TABLE IF NOT EXISTS workspace_memberships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role varchar(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_workspace_memberships_workspace_user UNIQUE (workspace_id, user_id)
);

DROP TRIGGER IF EXISTS trg_workspace_memberships_touch_updated_at ON workspace_memberships;
CREATE TRIGGER trg_workspace_memberships_touch_updated_at
BEFORE UPDATE ON workspace_memberships
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS ix_workspace_memberships_workspace_role
  ON workspace_memberships(workspace_id, role);

CREATE INDEX IF NOT EXISTS ix_workspace_memberships_user_id
  ON workspace_memberships(user_id);

CREATE TABLE IF NOT EXISTS workspace_invitations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  invited_email text NOT NULL,
  role varchar(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
  token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  accepted_at timestamptz,
  created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  accepted_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_workspace_invitations_workspace_id
  ON workspace_invitations(workspace_id);

CREATE INDEX IF NOT EXISTS ix_workspace_invitations_invited_email
  ON workspace_invitations(invited_email);

INSERT INTO workspaces (slug, name, is_default)
SELECT 'default', 'Default Workspace', true
WHERE NOT EXISTS (
  SELECT 1
  FROM workspaces
  WHERE is_default = true
);

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
INSERT INTO workspace_memberships (workspace_id, user_id, role)
SELECT
  default_workspace.id,
  users.id,
  CASE
    WHEN EXISTS (
      SELECT 1
      FROM user_roles
      WHERE user_roles.user_id = users.id
        AND user_roles.role = 'admin'
    ) THEN 'owner'
    ELSE 'member'
  END
FROM users
CROSS JOIN default_workspace
ON CONFLICT (workspace_id, user_id) DO NOTHING;

ALTER TABLE user_sessions
  ADD COLUMN IF NOT EXISTS current_workspace_id uuid REFERENCES workspaces(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_user_sessions_current_workspace_id
  ON user_sessions(current_workspace_id);

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
UPDATE user_sessions
SET current_workspace_id = default_workspace.id
FROM default_workspace
WHERE user_sessions.current_workspace_id IS NULL;

ALTER TABLE connector_oauth_states
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE;

ALTER TABLE connector_connections
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE;

ALTER TABLE connector_oauth_states
  DROP CONSTRAINT IF EXISTS connector_oauth_states_owner_scope_check;

ALTER TABLE connector_connections
  DROP CONSTRAINT IF EXISTS connector_connections_owner_scope_check;

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
UPDATE connector_oauth_states
SET workspace_id = default_workspace.id
FROM default_workspace
WHERE connector_oauth_states.workspace_id IS NULL;

WITH default_workspace AS (
  SELECT id
  FROM workspaces
  WHERE is_default = true
  ORDER BY created_at ASC
  LIMIT 1
)
UPDATE connector_connections
SET workspace_id = default_workspace.id
FROM default_workspace
WHERE connector_connections.workspace_id IS NULL;

UPDATE connector_oauth_states
SET owner_scope = CASE
  WHEN owner_scope = 'shared' THEN 'workspace'
  WHEN owner_scope = 'user' THEN 'personal'
  ELSE owner_scope
END;

UPDATE connector_connections
SET owner_scope = CASE
  WHEN owner_scope = 'shared' THEN 'workspace'
  WHEN owner_scope = 'user' THEN 'personal'
  ELSE owner_scope
END;

ALTER TABLE connector_oauth_states
  ADD CONSTRAINT connector_oauth_states_owner_scope_check
  CHECK (owner_scope IN ('workspace', 'personal'));

ALTER TABLE connector_connections
  ADD CONSTRAINT connector_connections_owner_scope_check
  CHECK (owner_scope IN ('workspace', 'personal'));

ALTER TABLE connector_connections
  ALTER COLUMN workspace_id SET NOT NULL;

DROP INDEX IF EXISTS uq_connector_connections_shared_provider;
DROP INDEX IF EXISTS uq_connector_connections_user_provider;

CREATE UNIQUE INDEX IF NOT EXISTS uq_connector_connections_workspace_provider
  ON connector_connections(workspace_id, provider, owner_scope)
  WHERE owner_user_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_connector_connections_personal_provider
  ON connector_connections(workspace_id, provider, owner_scope, owner_user_id)
  WHERE owner_user_id IS NOT NULL;

DROP INDEX IF EXISTS ix_connector_connections_owner_scope;
CREATE INDEX IF NOT EXISTS ix_connector_connections_workspace_scope
  ON connector_connections(workspace_id, owner_scope, owner_user_id);
