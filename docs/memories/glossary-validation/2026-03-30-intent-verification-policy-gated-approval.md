# Intent: Verification Policy-Gated Glossary Approval

## Context

Draft generation and approval existed, but approval was not yet enforced against an explicit verification policy.

## Decision

Each non-archived glossary concept is assigned a workspace-scoped default verification policy. Approval now requires both a canonical glossary document and a passing verification result. Drifted approved concepts stay readable, but they leave the verified state, reopen QA, and refresh a working draft.

## Implications

- request-only terms can still enter review and receive fallback drafts
- weak evidence no longer qualifies a concept for member-visible approval
- the review UI needs verification summary data in addition to trust badges
