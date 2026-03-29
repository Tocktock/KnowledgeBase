# Connector Flows

## Role-aware page states

### Anonymous

- The page explains the value of connected sources.
- Provider cards and recommended templates are visible.
- Protected actions redirect to `/login` with connector continuation parameters.

### Member

- Workspace sources are visible as read-only.
- Personal source management remains optional and secondary.
- Admin-only controls are hidden.

### Owner/Admin

- The page exposes provider setup, resource creation, visibility updates, and sync actions.
- Workspace and personal scopes are both visible, but workspace setup is primary.

## Live-source setup flow

1. Choose a provider card.
2. Start provider OAuth if a connection does not already exist.
3. Browse or search provider resources.
4. Select the source.
5. Confirm sync policy and visibility scope.
6. Create the connector resource.
7. Optionally trigger or wait for the first sync.

## Upload-backed evidence flow

1. Choose the Notion export upload template.
2. Upload the exported snapshot file.
3. The backend creates a resource with `selection_mode = export_upload`.
4. The uploaded snapshot becomes glossary evidence.
5. Future refreshes happen through another upload, not through manual sync.

## Validation interaction

1. Connector resources contribute documents to either the member-visible corpus or the evidence-only corpus.
2. Workspace validation runs resolve active workspace resources.
3. Live resources may be synced during the validation run.
4. Snapshot resources are counted as existing evidence but are skipped for live sync.
