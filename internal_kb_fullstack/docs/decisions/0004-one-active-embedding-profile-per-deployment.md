# 0004 - One active embedding profile per deployment

## Status
Accepted

## Decision
A deployment has one active embedding dimensionality.

The schema still stores `embedding_model` and `embedding_dimensions` on rows for traceability, but database constraints enforce a single active dimension for the installation.

## Why
The earlier schema looked like it supported arbitrary mixed embedding dimensions, but the vector column itself is fixed-width.

That mismatch would have caused confusion and invalid assumptions.

## Consequences
- Vector columns stay fixed-width.
- Changing dimensions requires a real migration and index rebuild.
- The stored dimension fields are treated as metadata and safety checks, not dynamic row-level flexibility.
