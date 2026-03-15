"""Backward-compatible browse exports.

New code should import from `app.services.catalog` and `app.services.wiki_graph` directly.
This module exists only to avoid breakage while the service layer is being split into
clearer bounded contexts.
"""

from app.services.catalog import get_document_by_slug, list_documents, lookup_documents_by_slugs
from app.services.wiki_graph import extract_heading_items, extract_internal_links, extract_internal_slugs, get_document_relations

__all__ = [
    "get_document_by_slug",
    "list_documents",
    "lookup_documents_by_slugs",
    "extract_heading_items",
    "extract_internal_links",
    "extract_internal_slugs",
    "get_document_relations",
]
