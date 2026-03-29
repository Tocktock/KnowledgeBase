# Concepts Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/glossary.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend pages

### `GET /glossary`

- Purpose: member-facing Concepts list page.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - the page emphasizes approved concepts and links to the dedicated request page for missing terms

### `GET /glossary/requests`

- Purpose: dedicated member-facing intake page for requesting a new concept and checking the current user's request history.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - signed-in workspace members see the request form and a `My requests` section
  - anonymous users see a login CTA instead of the form and request history
  - request submission delegates to `POST /v1/glossary/requests`
  - request history reads from `GET /v1/glossary/requests`

### `GET /glossary/[slug]`

- Purpose: member-facing concept detail page.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.

## Backend glossary read APIs

### `GET /v1/glossary`

- Purpose: list glossary concepts for member-facing browsing.
- Caller: anonymous or authenticated user.
- Response model: glossary list response defined in `glossary.py`
- Important behavior:
  - concept summaries include lifecycle and validation metadata, trust, and support counts
  - the member-facing list is intended to emphasize approved or otherwise consumable concepts

### `GET /v1/glossary/slug/{slug}`

- Purpose: resolve one concept by slug.
- Caller: anonymous or authenticated user.
- Response model: glossary concept detail defined in `glossary.py`
- Important error states:
  - unknown concept slug

### `GET /v1/glossary/{concept_id}`

- Purpose: resolve one concept by id.
- Caller: anonymous or authenticated user.
- Response model: glossary concept detail defined in `glossary.py`

## Shared concept-facing shapes

- `GlossaryConceptSummary`
- `GlossaryConceptDetail`
- `GlossarySupportItem`

Important support item behavior:

- support rows may reference member-visible or evidence-only underlying evidence
- the concept surface may show trust/source context even when the underlying evidence document does not appear in normal docs/search listings
