from __future__ import annotations

from urllib.parse import quote, unquote, urlsplit


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_source_system(value: str | None) -> str:
    cleaned = _clean_text(value)
    return cleaned.lower() if cleaned is not None else "unknown"


def build_generic_source_url(source_system: str | None, locator: str | None) -> str | None:
    cleaned_locator = _clean_text(locator)
    if cleaned_locator is None:
        return None
    return f"generic://{normalize_source_system(source_system)}/{quote(cleaned_locator, safe='')}"


def canonicalize_source_url(
    *,
    source_system: str | None,
    source_url: str | None,
    source_external_id: str | None = None,
    slug: str | None = None,
) -> str | None:
    normalized_source_url = _clean_text(source_url)
    if normalized_source_url is not None:
        parsed = urlsplit(normalized_source_url)
        scheme = parsed.scheme.lower()
        if scheme == "https" and parsed.netloc:
            return normalized_source_url
        if scheme == "generic" and parsed.netloc:
            locator = _clean_text(unquote(parsed.path.lstrip("/")))
            if locator is not None:
                return build_generic_source_url(parsed.netloc, locator)
        return build_generic_source_url(source_system, normalized_source_url)

    generic_from_external_id = build_generic_source_url(source_system, source_external_id)
    if generic_from_external_id is not None:
        return generic_from_external_id
    return build_generic_source_url(source_system, slug)


def is_external_source_url(value: str | None) -> bool:
    normalized = _clean_text(value)
    if normalized is None:
        return False
    parsed = urlsplit(normalized)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def is_generic_source_url(value: str | None) -> bool:
    normalized = _clean_text(value)
    if normalized is None:
        return False
    parsed = urlsplit(normalized)
    return parsed.scheme.lower() == "generic" and bool(parsed.netloc)


def connector_document_source_system(provider: str, *, selection_mode: str | None = None) -> str:
    normalized_provider = normalize_source_system(provider)
    if normalized_provider == "google_drive":
        return "google-drive"
    if normalized_provider == "notion" and selection_mode == "export_upload":
        return "notion-export"
    return normalized_provider
