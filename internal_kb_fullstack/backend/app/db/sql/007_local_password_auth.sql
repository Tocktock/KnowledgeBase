ALTER TABLE users
  ALTER COLUMN google_subject DROP NOT NULL;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS password_hash text;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS password_updated_at timestamptz;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id
  ON password_reset_tokens(user_id);

CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_workspace_id
  ON password_reset_tokens(workspace_id);
