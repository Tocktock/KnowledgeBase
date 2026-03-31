from __future__ import annotations

from uuid import uuid4

from app.db.models import ConnectorSourceItem, Document
from app.services.source_urls import canonicalize_source_url, connector_document_source_system
from scripts import backfill_source_urls


def test_canonicalize_source_url_preserves_https_values() -> None:
    source_url = canonicalize_source_url(
        source_system="github",
        source_url="https://github.com/example/repo/blob/main/README.md",
        source_external_id="README.md",
        slug="readme",
    )

    assert source_url == "https://github.com/example/repo/blob/main/README.md"


def test_canonicalize_source_url_converts_legacy_locator_to_generic() -> None:
    source_url = canonicalize_source_url(
        source_system="glossary",
        source_url="glossary://concept/1234",
        source_external_id="concept:1234:draft",
        slug="glossary-term",
    )

    assert source_url == "generic://glossary/glossary%3A%2F%2Fconcept%2F1234"


def test_canonicalize_source_url_falls_back_to_source_external_id_then_slug_then_none() -> None:
    assert (
        canonicalize_source_url(
            source_system="notion-export",
            source_url=None,
            source_external_id="Folder/Doc Name.md",
            slug="doc-name",
        )
        == "generic://notion-export/Folder%2FDoc%20Name.md"
    )
    assert (
        canonicalize_source_url(
            source_system="manual",
            source_url=None,
            source_external_id=None,
            slug="workspace-note",
        )
        == "generic://manual/workspace-note"
    )
    assert canonicalize_source_url(
        source_system="manual",
        source_url=None,
        source_external_id=None,
        slug=None,
    ) is None


def test_backfill_document_source_url_helper_is_idempotent() -> None:
    document = Document(
        id=uuid4(),
        workspace_id=uuid4(),
        source_system="glossary",
        source_external_id="concept:1:draft",
        source_url="glossary://concept/1",
        slug="glossary-term",
        title="Glossary term",
        language_code="ko",
        doc_type="glossary",
        status="draft",
        visibility_scope="member_visible",
        owner_team=None,
        meta={},
        current_revision_id=None,
    )

    first = backfill_source_urls.canonical_document_source_url(document)
    document.source_url = first
    second = backfill_source_urls.canonical_document_source_url(document)

    assert first == "generic://glossary/glossary%3A%2F%2Fconcept%2F1"
    assert second == first


def test_backfill_connector_source_url_helper_is_idempotent() -> None:
    item = ConnectorSourceItem(
        id=uuid4(),
        connection_id=uuid4(),
        resource_id=uuid4(),
        external_item_id="Folder/Spec.md",
        mime_type="text/markdown",
        name="Spec",
        source_url="Folder/Spec.md",
        source_revision_id="rev-1",
        internal_document_id=None,
        item_status="imported",
        unsupported_reason=None,
        error_message=None,
        provider_metadata={},
    )

    source_system = connector_document_source_system("notion", selection_mode="export_upload")
    first = backfill_source_urls.canonical_connector_item_source_url(
        item,
        provider="notion",
        selection_mode="export_upload",
    )
    item.source_url = first
    second = backfill_source_urls.canonical_connector_item_source_url(
        item,
        provider="notion",
        selection_mode="export_upload",
    )

    assert source_system == "notion-export"
    assert first == "generic://notion-export/Folder%2FSpec.md"
    assert second == first
