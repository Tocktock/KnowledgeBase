# Connector Flows

## Role-aware page states

### Anonymous

- `/connectors` explains the value of connected sources.
- Provider cards and recommended templates are visible on the overview.
- Protected actions redirect to `/login` with connector continuation parameters and return to `/connectors/setup/[provider]`.

### Member

- Workspace sources are visible as read-only.
- Personal source management remains optional and secondary.
- Admin-only controls are hidden.

### Owner/Admin

- The page exposes provider setup, resource creation, visibility updates, and sync actions.
- Workspace and personal scopes are both visible, but workspace setup is primary.

## Live-source setup flow

1. Choose a provider card.
2. Move into `/connectors/setup/[provider]`.
3. Start provider OAuth if a connection does not already exist.
4. Browse or search provider resources.
5. Select the source.
6. Confirm sync policy and visibility scope.
7. Create the connector resource.
8. Continue per-resource management from `/connectors/[connectionId]`.

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
