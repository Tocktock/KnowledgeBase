from __future__ import annotations

from urllib.parse import SplitResult, urlsplit, urlunsplit


def _contains_control_chars(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def _normalize_fallback_path(default_path: str) -> str:
    candidate = default_path.strip()
    if candidate and candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return "/"


def normalize_local_redirect_target(value: str | None, *, default_path: str = "/") -> str:
    fallback = _normalize_fallback_path(default_path)
    if not value:
        return fallback

    candidate = value.strip()
    if not candidate or "\\" in candidate or _contains_control_chars(candidate):
        return fallback
    if not candidate.startswith("/") or candidate.startswith("//"):
        return fallback

    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not parsed.path or not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return fallback

    return urlunsplit(
        SplitResult(
            scheme="",
            netloc="",
            path=parsed.path,
            query=parsed.query,
            fragment=parsed.fragment,
        )
    )
