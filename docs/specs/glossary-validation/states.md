# Glossary Validation States

## Lifecycle status

Lifecycle status describes the publishing or editorial stage of the concept itself.

- `suggested`
- `drafted`
- `approved`
- `ignored`
- `stale`

## Validation state

Validation state describes whether the current concept definition still matches its supporting evidence.

- `ok`
  - current evidence supports the present definition
- `needs_update`
  - current evidence suggests the definition should change
- `missing_draft`
  - the concept requires a draft before editorial review can proceed
- `stale_evidence`
  - the approved concept remains published, but supporting evidence drifted and needs QA
- `new_term`
  - the run discovered a new term candidate that entered the queue as suggested content

## State interaction rules

- Lifecycle and validation state are separate dimensions.
- `approved + stale_evidence` is valid and expected when evidence changes after publication.
- `review_required` is the operational flag consumed by the review queue.
- Validation runs update validation metadata without automatically replacing the published concept document.

## Validation run modes

- `sync_validate_impacted`
  - sync active workspace live resources and validate only impacted terms
- `sync_validate_full`
  - sync active workspace live resources and validate every term
- `validate_term`
  - validate one concept without a workspace-wide live sync
